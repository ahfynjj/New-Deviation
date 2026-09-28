"""FMC/GPIO recovery for warm-reset TX15 RAM tests, never a live application.

Caller must halt CPU, stop SysTick and keep PH12 high. Stop/reset FMC before
lowering PLL clocks. Restores controller configuration, not SDRAM contents;
the original reset handler must reinitialize external RAM. Failure forbids resume.
"""
AHB3, AHB4, RST = 0x580244d4, 0x580244e0, 0x5802447c
GPIO_REGS = tuple(0x58020800+p*0x400+offset for p in range(6)
                  for offset in (32,36,4,8,12,0))
FMC_REGS = (0x52004000,0x52004140,0x52004144,0x52004148,0x5200414c,0x52004154)

class SdramCaptureRecoveryError(RuntimeError):
    """Clock capture cleanup failed: caller must prohibit CPU resume."""


def capture_sdram_reset(read,write):
    saved={a:read(a) for a in (AHB3,AHB4,RST)}
    if saved[AHB3]&0x1000 or saved[RST]&0x1000:
        raise RuntimeError('FMC not reset-idle before RAM diagnostic')
    try:
        write(AHB4,saved[AHB4]|0xfc); read(AHB4)
        write(AHB3,saved[AHB3]|0x1000); read(AHB3)
        saved.update({a:read(a) for a in GPIO_REGS+FMC_REGS})
        if saved[0x52004000]&0x80000000:
            raise RuntimeError('FMC already enabled')
    finally:
        failures=[]
        for a in (AHB3,AHB4):
            try:
                write(a,saved[a])
                if read(a)!=saved[a]:
                    raise RuntimeError('readback mismatch')
            except Exception as exc:
                failures.append(f'{a:#x}: {exc}')
        if failures:
            raise SdramCaptureRecoveryError('; '.join(failures))
    return saved


def restore_sdram_reset(read,write,saved):
    write(AHB3,read(AHB3)|0x1000); read(AHB3)
    write(RST,read(RST)|0x1000)
    if not read(RST)&0x1000: raise RuntimeError('FMC reset assertion failed')
    write(RST,saved[RST])
    if read(RST)!=saved[RST] or read(0x52004000)&0x80000000:
        raise RuntimeError('FMC reset/release failed')
    for a in FMC_REGS: write(a,saved[a])
    write(AHB4,read(AHB4)|0xfc); read(AHB4)
    for a in GPIO_REGS: write(a,saved[a])
    if any(read(a)!=saved[a] for a in FMC_REGS+GPIO_REGS):
        raise RuntimeError('FMC/GPIO restore readback mismatch')
    write(AHB3,saved[AHB3]); write(AHB4,saved[AHB4])
    if any(read(a)!=saved[a] for a in (AHB3,AHB4,RST)):
        raise RuntimeError('FMC/GPIO clock restore readback mismatch')
    return {hex(a):hex(saved[a]) for a in saved}
