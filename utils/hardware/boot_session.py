"""Warm-reset boot bench evidence and recovery; no Flash commands.

Caller owns CPU halt, PH12 hold and complete GPIO/clock reset restoration.
Never use capture/restore on a running application or mapped QSPI execution.
"""
import struct
from probe_report import FIELDS

AHB3, AHB4, RST = 0x580244d4, 0x580244e0, 0x5802447c
GODR, GBSRR = 0x58021814, 0x58021818
QCR, QDCR, QSR, QCCR = 0x52005000, 0x52005004, 0x52005008, 0x52005014
CONTROL_ADDRS = {AHB3, AHB4, RST, GBSRR}


class CaptureRecoveryError(RuntimeError):
    """GPIO clock cleanup failed; do not resume the original CPU context."""


def validate_warm_power(safety):
    target = safety[0x58024818] & 0xc000
    if (safety[0x5802480c] & 7 != 2 or not target
            or safety[0x58024818] & 0xe000 != target | 0x2000
            or safety[0x58024804] & 0xe000 != target | 0x2000
            or not 2 <= (safety[0x52002000] & 15) <= 7):
        raise ValueError('Boot bench requires finalized LDO, ready VOS1..3 and latency 2..7')


def restore_power(read, write, saved, budget=100):
    validate_warm_power(saved)
    # Lower the voltage only after PLL/HSE recovery to HSI64. Never touch supply
    # selection or Flash read latency; both were constrained before image load.
    if (budget <= 0 or read(0x58024400) & 0x3f0f001d != 5 or read(0x58024410) & 0x3f
            or read(0x5802480c) != saved[0x5802480c]
            or read(0x52002000) != saved[0x52002000]):
        raise RuntimeError('Unsafe clock/supply/Flash state for voltage restore')
    if read(0x58024818) != saved[0x58024818]:
        write(0x58024818, saved[0x58024818])
    target = saved[0x58024818] & 0xe000
    for _ in range(budget):
        if read(0x58024818) & 0xe000 == target and read(0x58024804) & 0xe000 == target:
            restored = {a: read(a) for a in saved}
            if restored != saved: raise RuntimeError('Power/Flash restore readback mismatch')
            return {hex(a): hex(v) for a,v in restored.items()}
    raise RuntimeError('Original voltage readiness restore timeout')


def capture(read, write):
    saved = {a: read(a) for a in (AHB3, AHB4, RST)}
    if (saved[AHB3] | saved[RST]) & 0x4000:
        raise RuntimeError('QSPI not reset-idle; no boot bench')
    try:
        write(AHB4, saved[AHB4] | 0x40)
        if read(AHB4) != saved[AHB4] | 0x40:
            raise RuntimeError('GPIOG clock enable failed')
        saved[GODR] = read(GODR) & 0x40
    finally:
        try:
            write(AHB4, saved[AHB4])
            if read(AHB4) != saved[AHB4]:
                raise RuntimeError('GPIO clock cleanup readback mismatch')
        except Exception as exc:
            raise CaptureRecoveryError(str(exc)) from exc
    return saved


def restore(read, write, saved):
    # Force a reset even if firmware faulted halfway through an indirect read.
    # Do this before GPIO/FMC restoration and before lowering the PLL clock.
    write(AHB3, read(AHB3) | 0x4000)
    if not read(AHB3) & 0x4000: raise RuntimeError('QSPI clock enable failed')
    write(RST, read(RST) | 0x4000)
    if not read(RST) & 0x4000: raise RuntimeError('QSPI reset assertion failed')
    write(RST, read(RST) & ~0x4000)
    if read(RST) & 0x4000 or any(read(a) for a in (QCR, QDCR, QCCR)) or read(QSR) & 0x20:
        raise RuntimeError('QSPI reset/release readback mismatch')
    write(AHB3, (read(AHB3) & ~0x4000) | (saved[AHB3] & 0x4000))
    if read(AHB3) & 0x4000 != saved[AHB3] & 0x4000:
        raise RuntimeError('QSPI clock restore failed')
    gpio_clocks = read(AHB4)
    try:
        write(AHB4, gpio_clocks | 0x40)
        if not read(AHB4) & 0x40: raise RuntimeError('GPIOG clock enable failed')
        write(GBSRR, 0x40 if saved[GODR] else 0x00400000)
        if read(GODR) & 0x40 != saved[GODR]:
            raise RuntimeError('PG6 latch restore failed')
    finally:
        write(AHB4, gpio_clocks)
        if read(AHB4) != gpio_clocks: raise RuntimeError('GPIO clock restore failed')
    return {'qspi_reset': True, 'pg6_latch': hex(saved[GODR])}


def decode(data):
    if len(data) != 128: raise ValueError('Boot mailbox must be 128 bytes')
    values = dict(zip(FIELDS, struct.unpack('<20I', data[:80])))
    if values['magic'] != 0x4e445631 or values['version'] != 8:
        raise ValueError('Not a fresh version 8 boot mailbox')
    values['power_status'] = values.pop('reserved')
    values['unused_sdram_zero'] = data[80:] == bytes(48)
    return values


def is_live(current, previous):
    if previous is None: return False
    for r in (current, previous):
        if (r['magic'] != 0x4e445631 or r['version'] != 8 or r['state'] != 3 or r['error']
                or r['cpuid'] != 0x411fc271 or r['device_id'] & 0xfff != 0x450
                or r['scb_ccr'] & 0x30000 or r['mpu_ctrl'] & 1 or r['ram_words']
                or not r['unused_sdram_zero'] or r['power_status'] & 15 != 15
                or any(r[k] for k in ('fault_exception', 'cfsr', 'hfsr', 'mmfar', 'bfar'))
                or r['rcc_cr'] & 0x3f0f001d != 0x3030005
                or r['rcc_cfgr'] & 0x3f != 0x1b or r['rcc_d1cfgr'] & 0xf7f != 0x48):
            return False
    return (current['device_id'] == previous['device_id'] and
            all(0 < ((current[k]-previous[k]) & 0xffffffff) < 0x80000000 for k in ('ticks', 'loops')))


def decode_qspi(data, expected_header):
    if len(data) != 72 or len(expected_header) != 64:
        raise ValueError('Expected 72-byte QSPI report and 64-byte backup prefix')
    result, jedec = struct.unpack('<2I', data[:8])
    if result or jedec > 0xffffff or (jedec >> 16) in (0, 255) or (jedec & 255) in (0, 255):
        raise ValueError('QSPI read did not return a plausible JEDEC identity')
    if data[8:] != expected_header:
        raise ValueError('Raw SPI read differs from the backed-up mapped prefix')
    return {'result': result, 'jedec_id': hex(jedec), 'header_hex': data[8:].hex(),
            'backup_prefix_matches': True}
