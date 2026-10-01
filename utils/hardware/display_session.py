"""Reset-context capture/recovery for the RAM-only TX15 display demo.

Caller halts CPU, stops SysTick, keeps PH12 high, then restores SDRAM/PLL1/CPU.
Any exception forbids resuming the original firmware.
"""
import struct
from probe_report import FIELDS, SDRAM_FIELDS
CR, SEL, CFG, DIV3 = 0x58024400, 0x58024428, 0x5802442c, 0x58024440
AHB4, APB3, RST3 = 0x580244e0, 0x580244e4, 0x5802448c
PORTS = (0, 1, 8, 9, 10)
GPIO_REGS = tuple(0x58020000+p*0x400+off for p in PORTS for off in (0,4,8,12,20,32,36))
CONTROL_ADDRS = set(GPIO_REGS) | {CR,SEL,CFG,DIV3,AHB4,APB3,RST3,0x50001018}
CONTROL_ADDRS.update(0x58020018+p*0x400 for p in PORTS)

class DisplayCaptureRecoveryError(RuntimeError):
    pass

def capture(read, write):
    saved={a:read(a) for a in (AHB4,APB3,RST3,SEL,CFG,DIV3)}
    if read(CR)&0x30000000 or saved[APB3]&8 or saved[RST3]&8:
        raise RuntimeError('Display capture requires reset PLL3/LTDC')
    try:
        write(AHB4,saved[AHB4]|0x703)
        read(AHB4)
        saved.update((a,read(a)) for a in GPIO_REGS)
    finally:
        try:
            write(AHB4,saved[AHB4])
            if read(AHB4)!=saved[AHB4]: raise RuntimeError('GPIO clock mismatch')
        except Exception as exc:
            raise DisplayCaptureRecoveryError(str(exc)) from exc
    return saved

def restore(read, write, saved, budget=100):
    write(AHB4,read(AHB4)|0x703); read(AHB4)
    write(0x58020018,1<<26) # PA10 low before disconnecting backlight
    write(APB3,read(APB3)|8); read(APB3)
    write(0x50001018,read(0x50001018)&~1)
    write(RST3,saved[RST3]|8)
    if not read(RST3)&8: raise RuntimeError('LTDC reset assertion failed')
    write(RST3,saved[RST3])
    if read(RST3)!=saved[RST3] or read(0x50001018)&1:
        raise RuntimeError('LTDC reset release/readback failed')
    write(CR,read(CR)&~(1<<28))
    for _ in range(budget):
        if not read(CR)&0x30000000: break
    else: raise RuntimeError('PLL3 stop timeout')
    write(DIV3,saved[DIV3])
    write(SEL,(read(SEL)&~0x03f00000)|(saved[SEL]&0x03f00000))
    write(CFG,(read(CFG)&~0x01c00f00)|(saved[CFG]&0x01c00f00))
    for p in PORTS:
        b=0x58020000+p*0x400
        # Latches first, MODER last, while CPU remains halted.
        v=saved[b+20]&0xffff
        write(b+24,v|((~v&0xffff)<<16))
        for off in (32,36,4,8,12,0): write(b+off,saved[b+off])
    if any(read(a)!=saved[a] for a in GPIO_REGS) or read(DIV3)!=saved[DIV3]:
        raise RuntimeError('Display GPIO/PLL3 restoration mismatch')
    if ((read(SEL)^saved[SEL])&0x03f00000 or (read(CFG)^saved[CFG])&0x01c00f00):
        raise RuntimeError('PLL3 configuration restoration mismatch')
    write(APB3,saved[APB3]); write(AHB4,saved[AHB4])
    if read(APB3)!=saved[APB3] or read(AHB4)!=saved[AHB4]:
        raise RuntimeError('Display clock restoration mismatch')
    return True

def decode(data):
    if len(data)!=128: raise ValueError('Expected 128-byte display mailbox')
    r=dict(zip(FIELDS+SDRAM_FIELDS,struct.unpack('<32I',data)))
    if r['magic']!=0x4e445631 or r['version'] not in (6,7): raise ValueError('Not display V6')
    r['power_status']=r.pop('reserved')
    return r

def is_live(current, previous):
    if current['version']!=previous['version']: return False
    for r in (current,previous):
        if (r['state']!=3 or r['error'] or r['power_status']&15!=15
            or r['ram_words']!=76800 or r['sdram_state']!=3 or r['sdram_error']
            or r['sdram_words']!=76800 or r['sdram_checks']!=76800
            or r['rcc_cr']&0x3f0f001d!=0x33030005
            or r['rcc_cfgr']&0x3f!=0x1b or r['rcc_d1cfgr']&0xf7f!=0x48
            or r['fault_exception'] or r['cfsr'] or r['hfsr']): return False
    return all(0 < ((current[k]-previous[k])&0xffffffff) < 0x80000000 for k in ('ticks','loops'))

def capture_clock(read):
    from pll_clock import capture_pll128_clock
    # PLL1 validation is unchanged; separately validate all added PLL3 fields.
    if (read(CR)&0x30000000!=0x30000000 or read(SEL)&0x03f00000!=12<<20
        or read(CFG)&0x01c00f00!=0x01000800 or read(DIV3)!=0x1701023f):
        raise RuntimeError('Display pixel clock mismatch')
    r=capture_pll128_clock(lambda a: read(a)&~0x30000000 if a==CR else read(a))
    r[CR]=read(CR); r[DIV3]=read(DIV3)
    return r
