"""Restore reset-like HSI clocks after this project's direct-HSE RAM diagnostic.

Caller must halt the core and keep board power held. A failure must prohibit
resuming the original reset handler. This is not a general clock reset utility.
"""
CR, CFGR, D1CFGR = 0x58024400, 0x58024410, 0x58024418


def restore_reset_clock(read, write, budget=100):
    if (budget <= 0 or read(CR) & 0x3f0c0018 or read(D1CFGR) & 0xf0f
            or read(CFGR) & 7 not in (0, 2) or read(CFGR) & 0x38 not in (0, 0x10)):
        raise RuntimeError('Clock recovery encountered unsupported clock state')

    def wait(address, mask, expected):
        for _ in range(budget):
            if read(address) & mask == expected:
                return
        raise RuntimeError(f'Clock recovery timeout: {address:#x}, mask={mask:#x}')

    write(CR, read(CR) | 1)
    wait(CR, 5, 5)
    write(CFGR, read(CFGR) & ~7)
    wait(CFGR, 0x3f, 0)
    write(CR, read(CR) & ~(1 << 16))
    wait(CR, 0x30000, 0)
    result = {'rcc_cr': read(CR), 'rcc_cfgr': read(CFGR), 'rcc_d1cfgr': read(D1CFGR)}
    if result['rcc_cr'] & 0x1d != 5 or result['rcc_cfgr'] & 0x3f:
        raise RuntimeError('Reset clock readback mismatch')
    return result
