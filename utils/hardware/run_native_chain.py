"""TX15 bench: button-assisted reset catch, PH12 hold, then resume original boot.

Runs a pinned RF-off RAM chain and restores original reset entry. No Flash/option writes.
Requires --arm. Only this verified TX15/PWLINK2 configuration. No installation capability.
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from pyocd.core.helpers import ConnectHelper
from pyocd.probe.debug_probe import DebugProbe
from pyocd.coresight.minimal_mem_ap import MinimalMemAP

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--arm', action='store_true')
parser.add_argument('--display-diagnostic',action='store_true',help='Read LCD state and compare 15-second CPU pause; no LCD configuration writes')
parser.add_argument('--backlight-diagnostic',action='store_true',help='Fixed 13/101 PWM only during red-strip pause; then restore TIM1/PA10')
parser.add_argument('--flash-info',action='store_true',help='Small RAM status/SFDP reader only; no application or Flash writes')
args = parser.parse_args()
if args.flash_info and (args.display_diagnostic or args.backlight_diagnostic):parser.error('Flash-info is a separate mode')
if not args.arm: parser.error('Hardware operation requires --arm')
args.ram_probe=True
import chain_ram_session as ram_session
if args.flash_info:
    import flash_info_bundle
    flash_info_bundle.validate(ram_session.REPO)
else:ram_session.validate_image()  # Pin all images and backup before opening probe.

DHCSR, DEMCR = 0xe000edf0, 0xe000edfc
DBG3, DBG4 = 0x5c001034, 0x5c001054
AHB4 = 0x580244e0
HMODE, HTYPE, HPULL = 0x58021c00, 0x58021c04, 0x58021c0c
HIDR, HODR, HSET = 0x58021c10, 0x58021c14, 0x58021c18
AIDR = 0x58020010
AMODE, APULL = 0x58020000, 0x5802000c
WRITABLE = {DHCSR, DEMCR, DBG3, DBG4, AHB4, HMODE, HTYPE, HPULL, HSET, AMODE, APULL}
r = {'utc': datetime.now(timezone.utc).isoformat(), 'operation': __doc__, 'writes': []}
if args.ram_probe:
    r['operation'] = ('Button-assisted reset catch and PH12 hold, reviewed RAM image load/run, '
                      'mailbox capture, original reset-entry context restore; no Flash/option writes')
s = ap = dp = None
saved = {}
modified = False
reset_attempted = False
released = False

def write(addr, value):
    assert addr in WRITABLE
    item = {'address': hex(addr), 'value': hex(value), 'completed': False}
    r['writes'].append(item)
    ap.write32(addr, value)
    dp.flush()
    item['completed'] = True

def snapshot():
    return {name: hex(ap.read32(addr)) for name, addr in [
        ('CPUID', 0xe000ed00), ('DHCSR', DHCSR), ('VTOR', 0xe000ed08),
        ('RCC_CR', 0x58024400), ('RCC_CFGR', 0x58024410),
        ('RCC_D1CFGR', 0x58024418), ('SCB_CCR', 0xe000ed14),
        ('MPU_CTRL', 0xe000ed94), ('GPIOH_MODER', HMODE),
        ('GPIOH_IDR', HIDR), ('GPIOH_ODR', HODR), ('GPIOA_IDR', AIDR)]}

try:
    s = ConnectHelper.session_with_chosen_probe(
        unique_id='B8EFB57613B198CA10834F0545435DBB', blocking=False, auto_open=False,
        options={'target_override': 'cortex_m', 'frequency': 50000,
                 'connect_mode': 'attach', 'auto_unlock': False,
                 'no_config': True, 'resume_on_disconnect': False})
    if s is None:
        raise RuntimeError('Probe unavailable')
    s.open(init_board=False)
    dp = s.target.dp
    dp.connect(DebugProbe.Protocol.SWD)
    ap = MinimalMemAP(dp)
    ap.init()
    if (ap.read32(0x5c001000) & 0xfff) != 0x450:
        raise RuntimeError('Unexpected MCU family')
    if ap.read32(DHCSR) & 0x2f:
        raise RuntimeError('Debug control already active; refusing to override')
    if ap.read32(DHCSR) & (1 << 17) or s.probe.is_reset_asserted():
        raise RuntimeError('Core halted or reset already asserted')
    if (ap.read32(AHB4) & 0x81) != 0x81:
        raise RuntimeError('GPIOA/H clocks not enabled')
    if args.ram_probe:
        ram_session.verify_sdram_board(ap)
    if ((ap.read32(HMODE) >> 24) & 3) != 1 or not (ap.read32(HODR) & 0x1000):
        raise RuntimeError('PH12 not output high')
    if not ap.read32(AIDR) & 0x10:
        raise RuntimeError('Button already pressed; stop')
    saved = {addr: ap.read32(addr) for addr in (DEMCR, DBG3, DBG4)}
    r['saved'] = {hex(k): hex(v) for k, v in saved.items()}
    print('ARMED: press and hold power about 2 seconds; waiting up to 120 seconds.', flush=True)
    deadline = time.monotonic() + 120
    while ap.read32(AIDR) & 0x10:
        if time.monotonic() > deadline:
            raise TimeoutError('No press; no reset or target writes attempted')
        time.sleep(0.02)
    reset_attempted = True
    try:
        s.probe.assert_reset(True)
        time.sleep(0.05)
        if not s.probe.is_reset_asserted():
            raise RuntimeError('NRST did not read asserted')
        if ap.read32(0xe000ed00) != 0x411fc271:
            raise RuntimeError('Core unavailable under reset')
        modified = True
        write(DEMCR, saved[DEMCR] | 1)
        write(DHCSR, 0xa05f0001)
    finally:
        s.probe.assert_reset(False)
        released = True
        print('NRST RELEASED', flush=True)
    deadline = time.monotonic() + 0.5
    while not ap.read32(DHCSR) & (1 << 17):
        if time.monotonic() > deadline:
            raise RuntimeError('Reset vector catch did not halt core')
    # Preload output latch before switching pin mode, avoiding an output-low pulse.
    write(AHB4, ap.read32(AHB4) | (1 << 7) | 1)
    ap.read32(AHB4)
    write(HSET, 1 << 12)
    write(HTYPE, ap.read32(HTYPE) & ~(1 << 12))
    write(HPULL, ap.read32(HPULL) & ~(3 << 24))
    write(HMODE, (ap.read32(HMODE) & ~(3 << 24)) | (1 << 24))
    if not ap.read32(HIDR) & (1 << 12):
        raise RuntimeError('PH12 failed to read high')
    # Reset leaves PA4 analog; enable the confirmed active-low button input.
    write(APULL, (ap.read32(APULL) & ~(3 << 8)) | (1 << 8))
    write(AMODE, ap.read32(AMODE) & ~(3 << 8))
    # Reapply watchdog halt freeze and verify readback after reset release.
    write(DBG3, ap.read32(DBG3) | (1 << 6))
    write(DBG4, ap.read32(DBG4) | (1 << 18))
    if not (ap.read32(DBG3) & (1 << 6) and ap.read32(DBG4) & (1 << 18)):
        raise RuntimeError('Watchdog debug freeze did not read back')
    r['halted'] = snapshot()
    print('HALTED, PH12 HIGH: release power button now.', flush=True)
    deadline = time.monotonic() + 8
    while not ap.read32(AIDR) & 0x10:
        if time.monotonic() > deadline:
            raise TimeoutError('Button not released; resuming original boot')
        time.sleep(0.02)
    r['button_released'] = True
    time.sleep(1)
    r['after_button_release'] = snapshot()
    if not (int(r['after_button_release']['DHCSR'], 16) & (1 << 17)):
        raise RuntimeError('Core no longer halted after button release')
    if not (int(r['after_button_release']['GPIOH_IDR'], 16) & (1 << 12)):
        raise RuntimeError('Power hold not high after button release')
    r['status'] = 'halt_and_power_hold_verified'
    print('HALT AND POWER HOLD VERIFIED', r['after_button_release'], flush=True)
    if args.ram_probe:
        ram_session.run(ap, dp, r,display_diagnostic=args.display_diagnostic,backlight_diagnostic=args.backlight_diagnostic,flash_info_only=args.flash_info)
        r['status'] = 'ram_live_verified'
except Exception as exc:
    r['status'] = 'error'
    r['error'] = f'{type(exc).__name__}: {exc}'
    print(r['error'], flush=True)
finally:
    r['cleanup_errors'] = []
    if s is not None:
        if reset_attempted and not released:
            try:
                s.probe.assert_reset(False)
                released = True
            except Exception as exc:
                r['cleanup_errors'].append('NRST release: ' + str(exc))
        safe_to_resume = (r.get('ram_run', {}).get('context_restored', True)
                          and not r.get('ram_run', {}).get('recovery_errors', []))
        if modified and not safe_to_resume:
            r['cleanup_errors'].append('RAM context restore failed; refusing to resume unverified PC')
            print('CORE STATE NEEDS RECOVERY: not resuming unverified PC.', flush=True)
        if modified and safe_to_resume:
            # Restore vector catch then resume existing reset handler without changing PC.
            for addr, value in [(DEMCR, saved[DEMCR]), (DHCSR, 0xa05f0001),
                                (DHCSR, 0xa05f0000), (DBG3, saved[DBG3]),
                                (DBG4, saved[DBG4])]:
                try:
                    write(addr, value)
                except Exception as exc:
                    r['cleanup_errors'].append(hex(addr) + ': ' + str(exc))
            try:
                time.sleep(2)
                r['resumed'] = snapshot()
                print('RESUMED', r['resumed'], flush=True)
            except Exception as exc:
                r['cleanup_errors'].append('Resume read: ' + str(exc))
        s.close()
    r['reset_attempted'] = reset_attempted
    r['reset_released'] = released
    folder=Path(__file__).resolve().parents[2]/'local/hardware-session'
    folder.mkdir(parents=True,exist_ok=True)
    out = folder/('native-chain-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
    out.write_text(json.dumps(r, indent=2), encoding='utf-8')
    print('Saved', out.resolve(), flush=True)
raise SystemExit(0 if r.get('status') in ('halt_and_power_hold_verified', 'ram_live_verified') and not r['cleanup_errors'] else 1)
