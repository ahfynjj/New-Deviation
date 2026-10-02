"""Reset-entry USART6/NVIC recovery; caller halts CPU and stops SysTick first.

GPIO B/G/H configuration is restored by existing display/SDRAM helpers after
this helper has switched off the module. Any failure prohibits CPU resume.
"""
ENABLE,RESET=0x580244f0,0x58024498
ISER,ICER,ISPR,ICPR,IABR=0xe000e108,0xe000e188,0xe000e208,0xe000e288,0xe000e308
PRIORITY=0xe000e444
CR1=0x40011400
AHB4,BODR,BSET=0x580244e0,0x58020414,0x58020418
CAPTURE_ADDRS=(ENABLE,RESET,ISER,ISPR,IABR,PRIORITY,AHB4,BODR)
CONTROL_ADDRS={ENABLE,RESET,ICER,ICPR,PRIORITY,CR1,AHB4,BSET}

class RfCaptureRecoveryError(RuntimeError):
    """GPIO clock restoration failed; caller must prohibit original resume."""

def capture(read,write):
    saved={a:read(a) for a in CAPTURE_ADDRS if a!=BODR}
    if saved[ENABLE]&32 or saved[RESET]&32 or any(saved[a]&128 for a in (ISER,ISPR,IABR)):
        raise RuntimeError('USART6/IRQ71 must be reset-idle')
    try:
        write(AHB4,saved[AHB4]|2)
        if not read(AHB4)&2:raise RuntimeError('GPIOB clock did not enable')
        saved[BODR]=read(BODR)
        if saved[BODR]&(1<<13):raise RuntimeError('Module must be off at reset entry: '+hex(saved[BODR]))
    finally:
        try:
            write(AHB4,saved[AHB4])
            if read(AHB4)!=saved[AHB4]:raise RuntimeError('GPIO clock capture cleanup mismatch')
        except Exception as exc:
            raise RfCaptureRecoveryError(str(exc)) from exc
    return saved

def restore(read,write,saved):
    write(ICER,128)
    if read(ISER)&128 or read(IABR)&128:
        raise RuntimeError('USART6 IRQ not disabled or exception still active')
    write(AHB4,read(AHB4)|2);read(AHB4)
    write(BSET,1<<29)
    if read(BODR)&(1<<13):raise RuntimeError('Module power did not switch off')
    write(ENABLE,read(ENABLE)|32);read(ENABLE)
    write(CR1,0)
    write(RESET,read(RESET)|32)
    if not read(RESET)&32:raise RuntimeError('USART6 reset assertion failed')
    write(RESET,saved[RESET])
    if read(CR1):raise RuntimeError('USART6 did not reset')
    write(ICPR,128)
    write(PRIORITY,(read(PRIORITY)&0x00ffffff)|(saved[PRIORITY]&0xff000000))
    write(ENABLE,saved[ENABLE])
    if read(ISPR)&128 or any(read(a)!=saved[a] for a in (ENABLE,RESET)):
        raise RuntimeError('USART6 reset/clock/pending restore mismatch')
    if (read(PRIORITY)^saved[PRIORITY])&0xff000000:raise RuntimeError('USART6 priority restore mismatch')
    return {hex(a):hex(read(a)) for a in (ENABLE,RESET,ISER,ISPR,PRIORITY,BODR)}
