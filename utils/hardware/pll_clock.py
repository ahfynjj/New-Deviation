"""Readback/recovery for the bounded TX15 PLL128 warm-reset RAM diagnostic.

Caller must halt the core, stop SysTick and keep PH12 high before recovery.
Never resume the original firmware unless this and CPU restoration succeed.
"""
CR, CFGR = 0x58024400, 0x58024410
D1, D2, D3 = 0x58024418, 0x5802441c, 0x58024420
SEL, CFG, DIV = 0x58024428, 0x5802442c, 0x58024430
REGS = (CR, CFGR, D1, D2, D3, SEL, CFG, DIV)


def capture_reset_clock(read):
    r = {a: read(a) for a in REGS}
    if (r[CR] & 0x3f0f001d != 5 or r[CFGR] & 0x3f or r[D1] & 0xf7f
            or r[D2] & 0x770 or r[D3] & 0x70):
        raise RuntimeError('Not reset-like clock state for PLL diagnostic')
    return r


def capture_pll128_clock(read):
    r = {a: read(a) for a in REGS}
    if (r[CR] & 0x3f0f001d != 0x03030005 or r[CFGR] & 0x3f != 0x1b
            or r[D1] & 0xf7f != 0x48 or r[D2] & 0x770 != 0x440 or r[D3] & 0x70 != 0x40
            or r[SEL] & 0x3f3 != 0xc2 or r[CFG] & 0x7000f != 0x10008
            or r[DIV] & 0xffff != 0x23f):
        raise RuntimeError('PLL128 register readback mismatch')
    return r


def restore_pll_clock(read, write, saved, budget=100):
    capture_reset_clock(saved.__getitem__)
    if (budget <= 0 or read(CR) & 0x3c0c0018 or read(CFGR) & 7 not in (0, 2, 3)
            or read(CFGR) & 0x38 not in (0, 0x10, 0x18)):
        raise RuntimeError('Unsupported PLL recovery clock state')

    def wait(address, mask, expected):
        for _ in range(budget):
            if read(address) & mask == expected:
                return
        raise RuntimeError(f'PLL recovery timeout at {address:#x}, mask={mask:#x}')

    write(CR, read(CR) | 1)
    wait(CR, 5, 5)
    write(CFGR, read(CFGR) & ~7)
    wait(CFGR, 0x3f, 0)
    write(CR, read(CR) & ~(1 << 24))
    wait(CR, 0x3000000, 0)
    for address in (SEL, CFG, DIV, D3, D2, D1):
        write(address, saved[address])
    write(CR, read(CR) & ~(1 << 16))
    wait(CR, 0x30000, 0)
    restored = {a: read(a) for a in REGS}
    if restored != saved:
        raise RuntimeError('PLL reset clock restoration readback mismatch')
    return restored
