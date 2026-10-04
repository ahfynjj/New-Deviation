"""Native loader-to-standalone-app RAM chain; host feeds source, never Flash.

Caller owns reset/PH12 and finally restores debug settings. This module restores
the captured original reset-entry CPU context before returning, even on error.
"""
import struct
import sys
import time
from datetime import datetime
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'utils' / 'hardware'))
from pll_clock import capture_reset_clock, capture_pll128_clock, restore_pll_clock
from sdram_session import capture_sdram_reset, restore_sdram_reset, GPIO_REGS, FMC_REGS, AHB3, AHB4, RST, SdramCaptureRecoveryError
import display_session
import analog_session
import boot_session
import boot_chain
EXPECTED_ELF, EXPECTED_BIN = (boot_chain.ELF_SHA, boot_chain.BIN_SHA)
decode, is_live = (boot_chain.decode, boot_chain.is_live)
capture_pll128_clock = display_session.capture_clock
DHCSR, DCRSR, DCRDR = (0xe000edf0, 0xe000edf4, 0xe000edf8)
CORE_REGS = tuple(range(13)) + (14, 15, 16, 17, 18, 20)
CONTROL_ADDRS = {DHCSR, DCRSR, DCRDR, 0xe000ed08, 0xe000e010, 0xe000e014, 0xe000e018, 0xe000ed04, 0xe000ed28, 0xe000ed2c, 0x58024400, 0x58024410, 0x58024418, 0x5802441c, 0x58024420, 0x58024428, 0x5802442c, 0x58024430}
CONTROL_ADDRS.update(analog_session.CONTROL_ADDRS)
CONTROL_ADDRS.update(GPIO_REGS + FMC_REGS + (AHB3, AHB4, RST))
CONTROL_ADDRS.update(boot_session.CONTROL_ADDRS)
CONTROL_ADDRS.update(display_session.CONTROL_ADDRS)
HMODE, HSET, HODR, HIDR, AIDR = (0x58021c00, 0x58021c18, 0x58021c14, 0x58021c10, 0x58020010)

def validate_image():
    binary, layout, _, _ = boot_chain.validate_bundle(REPO)
    return (binary, layout)

def allowed_ram_word(address, image_size):
    return address % 4 == 0 and (0x24000000 <= address <= 0x24000000 + image_size - 4 or 0x2400e000 <= address <= 0x2400e07c or address in (boot_chain.CONTROL + 4, boot_chain.CONTROL + 8))

def verify_sdram_board(ap):
    if ap.read32(AHB3) & 0x1000 == 0 or ap.read32(AHB4) & 252 != 252:
        raise RuntimeError('Running firmware does not clock expected SDRAM ports')
    if ap.read32(0x52004144) & 0x7fff != 468 or ap.read32(0x5802444c) & 3:
        raise RuntimeError('Unrecognized SDRAM geometry/kernel source')
    for p, pins in enumerate((1, 0xc703, 0xff83, 0xf83f, 0x8133, 192)):
        base = 0x58020800 + p * 1024
        mode = ap.read32(base)
        af = (ap.read32(base + 32), ap.read32(base + 36))
        for pin in range(16):
            if pins & 1 << pin and (mode >> pin * 2 & 3 != 2 or af[pin // 8] >> pin % 8 * 4 & 15 != 12):
                raise RuntimeError(f'SDRAM GPIO mismatch port={p + 2}, pin={pin}')

def run(ap, dp, result):
    binary, layout, payload, prefix = boot_chain.validate_bundle(REPO)
    out = REPO / 'local' / 'ram-runs' / datetime.now().strftime('%Y%m%d-%H%M%S')
    out.mkdir(parents=True, exist_ok=False)
    result['ram_run'] = report = {'folder': str(out), 'elf_sha256': EXPECTED_ELF, 'bin_sha256': EXPECTED_BIN, 'context_restored': False}
    original = None
    changed = False
    capture_cleanup_error = None

    def write(address, value):
        if address not in CONTROL_ADDRS and (not allowed_ram_word(address, len(binary))) and address != 0x58024818:
            raise ValueError(f'Write address not allowed: {address:#x}')
        ap.write32(address, value)
        dp.flush()

    def wait_bit(mask):
        until = time.monotonic() + 0.5
        while True:
            value = ap.read32(DHCSR)
            if value & mask:
                return value
            if time.monotonic() > until:
                raise RuntimeError(f'DHCSR wait failed: {mask:#x}, last={value:#x}')

    def reg_read(number):
        if not ap.read32(DHCSR) & 1 << 17:
            raise RuntimeError('Core not halted for register read')
        write(DCRSR, number)
        wait_bit(1 << 16)
        return ap.read32(DCRDR)

    def reg_write(number, value):
        if number not in CORE_REGS or not ap.read32(DHCSR) & 1 << 17:
            raise RuntimeError('Invalid core register write/state')
        write(DCRDR, value)
        write(DCRSR, number | 1 << 16)
        wait_bit(1 << 16)

    def read_bytes(address, size):
        assert size % 4 == 0
        return b''.join((struct.pack('<I', ap.read32(a)) for a in range(address, address + size, 4)))
    try:
        if not ap.read32(DHCSR) & 1 << 17:
            raise RuntimeError('Core must be halted')
        if ap.read32(0x58024400) & 29 != 5 or ap.read32(0x58024410) & 63 or ap.read32(0x58024418) & 3855 or ap.read32(0xe000ed14) & 0x30000 or ap.read32(0xe000ed94) & 1:
            raise RuntimeError('Not in required reset clock/cache/MPU state')
        if not ap.read32(0x5200201c) & 1 << 4:
            raise RuntimeError('IWDG hardware start mode unsupported')
        if ap.read32(0xe000e010) & 7 or ap.read32(0xe000ed28) or ap.read32(0xe000ed2c):
            raise RuntimeError('SysTick/fault status not reset-clean')
        original_analog = analog_session.capture(ap.read32)
        original_clock = capture_reset_clock(ap.read32)
        report['original_clock'] = {hex(a): hex(v) for a, v in original_clock.items()}
        safety = {a: ap.read32(a) for a in (0x58024804, 0x5802480c, 0x58024818, 0x52002000)}
        report['power_flash_before'] = {hex(a): hex(v) for a, v in safety.items()}
        if not safety[0x58024804] & 0x2000 or not safety[0x58024804] & 0xc000 or safety[0x5802480c] & 3 != 2 or (not 1 <= safety[0x52002000] & 15 <= 7):
            raise RuntimeError('PLL128 voltage/Flash precondition not met; no image load')
        boot_session.validate_warm_power(safety)
        original = {reg: reg_read(reg) for reg in CORE_REGS}
        original_vtor = ap.read32(0xe000ed08)
        report['original_core'] = {str(k): hex(v) for k, v in original.items()}
        if original[15] & ~1 != ap.read32(0x8000004) & ~1 or original[17] != ap.read32(0x8000000):
            raise RuntimeError('Not halted at original Flash reset entry')
        if original[16] & 511 or original[20] != 0 or original_vtor != 0x8000000:
            raise RuntimeError('Unexpected reset CPU context')
        try:
            original_sdram = capture_sdram_reset(ap.read32, write)
        except SdramCaptureRecoveryError as exc:
            capture_cleanup_error = str(exc)
            raise
        try:
            original_display = display_session.capture(ap.read32, write)
        except display_session.DisplayCaptureRecoveryError as exc:
            capture_cleanup_error = str(exc)
            raise
        report['original_sdram'] = {hex(a): hex(v) for a, v in original_sdram.items()}
        try:
            original_qspi = boot_session.capture(ap.read32, write)
        except boot_session.CaptureRecoveryError as exc:
            capture_cleanup_error = str(exc)
            raise
        report['original_qspi'] = {hex(a): hex(v) for a, v in original_qspi.items()}
        for offset in range(0, len(binary), 4):
            write(0x24000000 + offset, struct.unpack_from('<I', binary, offset)[0])
        for address in range(0x2400e000, 0x2400e080, 4):
            write(address, 0)
        if read_bytes(0x24000000, len(binary)) != binary:
            raise RuntimeError('RAM image readback mismatch')
        if read_bytes(0x2400e000, 128) != bytes(128):
            raise RuntimeError('Mailbox clear readback mismatch')
        report['image_readback_verified'] = True
        print('RAM IMAGE READBACK VERIFIED', len(binary), 'bytes', flush=True)
        changed = True
        reg_write(20, 1)
        reg_write(17, 0x24010000)
        reg_write(16, 0x1000000)
        reg_write(15, int(layout['entry'], 16))
        write(DHCSR, 0xa05f0001)
        deadline = time.monotonic() + 20
        while ap.read32(boot_chain.CONTROL) != boot_chain.READY:
            if ap.read32(0x2400e008) in (4, 5):
                raise RuntimeError('Loader initialization fault: ' + str(read_bytes(0x2400e000, 128).hex()))
            if time.monotonic() > deadline:
                raise TimeoutError('Loader source gate timeout')
            time.sleep(0.05)
        write(DHCSR, 0xa05f0003)
        wait_bit(1 << 17)
        if ap.read32(0xe000ed04) & 511:
            raise RuntimeError('Loader source wait not in thread mode')
        control = read_bytes(boot_chain.CONTROL, 80)
        ready, size, gate, jedec = struct.unpack_from('<4I', control)
        if (ready, size, gate, jedec) != (boot_chain.READY, 0, 0, 0xc84018) or control[16:] != prefix:
            raise RuntimeError('QSPI/original-prefix/source-gate validation failed')
        report['qspi'] = {'jedec': hex(jedec), 'original_prefix_verified': True}
        report['source_loaded_bytes'] = boot_chain.upload(ap, dp, payload)
        report['source_sha256'] = boot_chain.PAYLOAD_SHA
        report['source_readback_verified'] = True
        write(boot_chain.CONTROL + 4, len(payload))
        write(boot_chain.CONTROL + 8, boot_chain.GO)
        if ap.read32(boot_chain.CONTROL + 4) != len(payload) or ap.read32(boot_chain.CONTROL + 8) != boot_chain.GO:
            raise RuntimeError('Source gate readback mismatch')
        write(DHCSR, 0xa05f0001)
        deadline = time.monotonic() + 20
        while ap.read32(0x2400e004) != 10 or ap.read32(0x2400e008) in (0, 1, 2):
            if ap.read32(0x2400e008) in (4, 5):
                raise RuntimeError('Native boot/app startup failed: ' + read_bytes(0x2400e000, 128).hex())
            if time.monotonic() > deadline:
                raise TimeoutError('Native boot/app startup timeout')
            time.sleep(0.05)
        print('NATIVE CHAIN APP READY: 75 seconds. Test wheel/ENTER/short EXIT and six analog inputs. Do not press POWER. RF off; no Flash writes.', flush=True)
        first = read_bytes(0x2400e000, 128)
        (out / 'mailbox-1.bin').write_bytes(first)
        report['first'] = decode(first)
        if ap.read32(0x58020414)&(1<<13):raise RuntimeError('Internal RF power unexpectedly on')
        report['internal_rf_off']=True
        report['pll_clock_first'] = {hex(a): hex(v) for a, v in capture_pll128_clock(ap.read32).items()}
        # Short waits keep fault detection and host progress responsive.
        deadline=time.monotonic()+75
        while time.monotonic()<deadline:
            if ap.read32(0x2400e008)!=3:raise RuntimeError('Native application left running state')
            time.sleep(0.5)
        second = read_bytes(0x2400e000, 128)
        (out / 'mailbox-2.bin').write_bytes(second)
        report['second'] = decode(second)
        report['pll_clock_second'] = {hex(a): hex(v) for a, v in capture_pll128_clock(ap.read32).items()}
        report['power_flash_after'] = {hex(a): hex(ap.read32(a)) for a in safety}
        expected_power = {a: v for a, v in safety.items()}
        for a in (0x58024804, 0x58024818):
            expected_power[a] = expected_power[a] & ~0xc000 | 0xc000
        if report['power_flash_after'] != {hex(a): hex(v) for a, v in expected_power.items()}:
            raise RuntimeError('Unexpected power/Flash register change')
        report['live'] = is_live(report['second'], report['first'])
        report['dhcsr_running'] = hex(ap.read32(DHCSR))
        print('RAM MAILBOX FIRST', report['first'], flush=True)
        print('RAM MAILBOX SECOND', report['second'], flush=True)
        if not report['live']:
            raise RuntimeError('Two live mailbox snapshots not established')
        if int(report['dhcsr_running'], 16) & (1 << 17 | 1 << 19):
            raise RuntimeError('Core halted/locked up while sampling')
    finally:
        recovery_errors = []
        if capture_cleanup_error is not None:
            recovery_errors.append('SDRAM capture recovery: ' + capture_cleanup_error)
        try:
            if changed:
                report['fault_before_cleanup']={hex(a):hex(ap.read32(a)) for a in (0xe000ed04,0xe000ed28,0xe000ed2c)}
                boot_chain.quiesce_thread(ap.read32,write,reg_write,lambda:wait_bit(1<<17),time.sleep)
                write(0xe000ed28, ap.read32(0xe000ed28))
                write(0xe000ed2c, ap.read32(0xe000ed2c))
                report['restored_analog'] = analog_session.restore(ap.read32, write, original_analog)
                report['restored_display'] = display_session.restore(ap.read32, write, original_display)
                report['restored_qspi'] = boot_session.restore(ap.read32, write, original_qspi)
                report['restored_sdram'] = restore_sdram_reset(ap.read32, write, original_sdram)
                report['restored_clock'] = {hex(a): hex(v) for a, v in restore_pll_clock(ap.read32, write, original_clock).items()}
                report['restored_power'] = boot_session.restore_power(ap.read32, write, safety)
                write(0xe000ed08, original_vtor)
                for reg, value in original.items():
                    reg_write(reg, value)
                if any((reg_read(reg) != value for reg, value in original.items())):
                    raise RuntimeError('Original reset-entry register restore mismatch')
            report['context_restored'] = not recovery_errors
        except Exception as exc:
            recovery_errors.append('Core recovery: ' + str(exc))
        report['recovery_errors'] = recovery_errors
        if recovery_errors:
            raise RuntimeError('; '.join(recovery_errors))
if __name__ == '__main__':
    image, layout = validate_image()
    for addr in (0x8000000, 0x90000000, 0x2400e080, 0x2400f000, 0x24000001):
        assert not allowed_ram_word(addr, len(image))
    assert allowed_ram_word(0x24000000, len(image))
    assert allowed_ram_word(0x2400e07c, len(image))
    print('Offline image/hash/write-range checks passed:', len(image), layout)
