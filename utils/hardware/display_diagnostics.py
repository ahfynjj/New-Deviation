"""Read-only LTDC/backlight evidence plus a bounded CPU-pause comparison.

RM0433 32.7.9/12/13: ISR 0x038, CPSR 0x044, CDSR 0x048.
https://www.st.com/resource/en/reference_manual/rm0433-stm32h742-stm32h743-753-and-stm32h750-value-line-advanced-armbased-32bit-mcus-stmicroelectronics.pdf
Never clears ISR, changes LCD configuration, or writes power GPIO. Optional
paused overlay writes only eight framebuffer rows, then restores them readback.
Sampled GPIO levels are digital evidence, not a measurement of backlight voltage.
ISR flags are sticky history, not a rate or proof that faults occurred in a phase.
"""
import struct
AHB4,APB3=0x580244e0,0x580244e4
AMODE,AIDR,AODR=0x58020000,0x58020010,0x58020014
GCR,ISR,CPSR,CDSR,TWCR=0x50001018,0x50001038,0x50001044,0x50001048,0x50001014
FB,PITCH,LINES=0x500010ac,0x500010b0,0x500010b4
DHCSR=0xe000edf0
OVERLAY_START=0xd0000000
OVERLAY_BYTES=480*8*2

APB2,RST2=0x580244f0,0x58024498
AAFRH=0x58020024
TIM1=0x40010000
CR,CFGR,D1,D2,PLLSEL,PLLCFG,PLLDIV=(0x58024400,0x58024410,0x58024418,0x5802441c,0x58024428,0x5802442c,0x58024430)
TIMER_REGS=tuple(TIM1+o for o in (0,4,8,12,0x18,0x1c,0x20,0x24,0x28,0x2c,0x30,0x34,0x38,0x3c,0x40,0x44))
BACKLIGHT_WRITES={APB2,RST2,AMODE,AAFRH,TIM1+0x14}|set(TIMER_REGS)

class BacklightTrial:
    """Fixed PA10/TIM1_CH3 ~990 Hz, 13/101 duty, on this PLL128 bench only.

    TIM1 must be unused. No power/LCD registers or Flash writes. Caller keeps
    CPU paused and treats failed restoration as a recovery error.
    """
    def __init__(self,read,write):self.read=read;self.write=write;self.saved=None;self.restored=False
    def enter(self):
        r=self.read
        if not r(DHCSR)&(1<<17) or r(APB2)&1 or r(RST2)&1:
            raise RuntimeError('PWM trial requires halted CPU and unused TIM1')
        if ((r(CR)&0x3f0f001d)!=0x33030005 or r(CFGR)&0x803f!=0x1b or
            r(D1)&0xf7f!=0x48 or r(D2)&0x770!=0x440 or
            r(PLLSEL)&0x3f3!=0xc2 or r(PLLCFG)&0x7000f!=0x10008 or
            r(PLLDIV)&0xffff!=0x23f or (r(AMODE)>>20)&3!=1):
            raise RuntimeError('PWM trial requires exact native clock and PA10 output')
        self.saved={a:r(a) for a in (APB2,RST2,AMODE,AAFRH)}
        self.restored=False
        self.write(APB2,self.saved[APB2]|1);r(APB2)
        self.saved.update((a,r(a)) for a in TIMER_REGS)
        if r(TIM1)&1 or r(TIM1+0x20) or r(TIM1+0x44)&0x8000:
            raise RuntimeError('TIM1 was already configured')
        # HCLK64 / APB2 divide2 * timer multiplier2 = 64 MHz.
        for a,v in ((TIM1,0x80),(TIM1+0x28,639),(TIM1+0x2c,100),
                    (TIM1+0x3c,13),(TIM1+0x1c,0x68),(TIM1+0x20,0x100),
                    (TIM1+0x14,1),(TIM1+0x44,0x8000),(TIM1,0x81)):
            self.write(a,v)
        self.write(AAFRH,(self.saved[AAFRH]&~(15<<8))|(1<<8))
        self.write(AMODE,(self.saved[AMODE]&~(3<<20))|(2<<20))
        for a,v in ((TIM1+0x28,639),(TIM1+0x2c,100),(TIM1+0x3c,13),
                    (TIM1+0x1c,0x68),(TIM1+0x20,0x100),(TIM1+0x44,0x8000),(TIM1,0x81)):
            if r(a)!=v:raise RuntimeError('PWM configuration readback mismatch')
    def exit(self):
        if self.saved is None:return
        if not self.read(DHCSR)&(1<<17):raise RuntimeError('PWM recovery requires halted CPU')
        s=self.saved
        self.write(AMODE,s[AMODE]);self.write(AAFRH,s[AAFRH])
        self.write(RST2,s[RST2]|1);self.read(RST2)
        self.write(RST2,s[RST2]);self.read(RST2)
        if any(self.read(a)!=s[a] for a in TIMER_REGS if a in s):
            raise RuntimeError('TIM1 reset restoration mismatch')
        self.write(APB2,s[APB2])
        if any(self.read(a)!=s[a] for a in (AMODE,AAFRH,APB2,RST2)):
            raise RuntimeError('Backlight pin/clock restoration mismatch')
        self.restored=True;self.saved=None

class PausedContrast:
    def __init__(self,overlay,trial):self.overlay=overlay;self.trial=trial
    def enter(self):self.overlay.enter();self.trial.enter()
    def exit(self):
        try:self.trial.exit()
        finally:self.overlay.exit()

class FrameOverlay:
    """Exact bounded RAM-only red strip; CPU must be halted throughout."""
    def __init__(self,ap,dp):self.ap=ap;self.dp=dp;self.original=None;self.restored=False
    def guard(self):
        if not self.ap.read32(DHCSR)&(1<<17) or self.dp.read_ap(0)&0x37!=0x12:
            raise RuntimeError('Overlay requires halted CPU and 32-bit MEM-AP')
        if self.ap.read32(FB)!=OVERLAY_START:raise RuntimeError('Overlay does not match active framebuffer')
    def read_chunk(self,at,n):
        self.dp.write_ap(4,at)
        return struct.pack('<%dI'%(n//4),*self.dp.read_ap_multiple(12,n//4))
    def store(self,data):
        if len(data)!=OVERLAY_BYTES:raise ValueError('Invalid overlay size')
        for off in range(0,OVERLAY_BYTES,256):
            at=OVERLAY_START+off;chunk=data[off:off+256]
            self.dp.write_ap(4,at);self.dp.write_ap_multiple(12,struct.unpack('<64I',chunk));self.dp.flush()
            if self.read_chunk(at,256)!=chunk:raise RuntimeError('Overlay readback mismatch')
    def enter(self):
        self.guard()
        if self.original is not None:raise RuntimeError('Overlay already active')
        self.restored=False
        self.original=b''.join(self.read_chunk(OVERLAY_START+off,256) for off in range(0,OVERLAY_BYTES,256))
        self.store(b'\0\xf8'*(OVERLAY_BYTES//2))
    def exit(self):
        if self.original is None:return
        self.guard();self.store(self.original);self.original=None;self.restored=True

def sample(read):
    if not read(AHB4)&1 or not read(APB3)&8:raise ValueError('GPIOA/LTDC clocks required')
    regs={a:read(a) for a in (AMODE,AIDR,AODR,GCR,ISR,CPSR,CDSR,TWCR,FB,PITCH,LINES)}
    position=regs[CPSR];total=regs[TWCR]
    return dict(registers={hex(a):hex(v) for a,v in regs.items()},
        backlight_mode=(regs[AMODE]>>20)&3,backlight_output_high=bool(regs[AODR]&(1<<10)),
        backlight_input_high=bool(regs[AIDR]&(1<<10)),
        fifo_underrun=bool(regs[ISR]&2),transfer_error=bool(regs[ISR]&4),
        position=[position>>16,position&0xffff],display_phase=regs[CDSR]&15,
        nominal_refresh_hz=(48000000/12*64/24)/(((total>>16)+1)*((total&0xffff)+1)))

def summarize(rows):
    samples=[r['sample'] for r in rows]
    return dict(samples=len(samples),
        sampled_backlight_high=bool(samples) and all(s['backlight_mode']==1 and
            s['backlight_output_high'] and s['backlight_input_high'] for s in samples),
        scan_position_changed=len({tuple(s['position']) for s in samples})>1,
        fifo_underrun_latched=any(s['fifo_underrun'] for s in samples),
        transfer_error_latched=any(s['transfer_error'] for s in samples),
        visual_confirmation_required=True)

def observe(read,write,wait_halt,sleep,now,durations=(20,15,35),rows=None,overlay=None):
    if len(durations)!=3 or any(not 0<n<=35 for n in durations):raise ValueError('Unbounded display observation')
    if read(DHCSR)&((1<<17)|(1<<19)):raise RuntimeError('Display observation requires running CPU')
    if rows is None:rows=[]
    begin=now()
    def phase(name,seconds):
        until=now()+seconds
        while now()<until:
            rows.append(dict(phase=name,seconds=now()-begin,sample=sample(read)))
            remaining=until-now()
            if remaining>0:sleep(min(1,remaining))
    print('DISPLAY RUNNING: observe flicker for 20 seconds, then a 15-second fixed picture.',flush=True)
    phase('running',durations[0])
    try:
        write(DHCSR,0xa05f0003);wait_halt()
        if overlay is not None:overlay.enter()
        print('DISPLAY PAUSED: CPU held for 15 seconds; LTDC keeps scanning. Observe whether flicker stops.',flush=True)
        phase('paused',durations[1])
    finally:
        # Resume this exact app context; no PC/stack/peripheral replacement here.
        if overlay is not None:overlay.exit()
        write(DHCSR,0xa05f0001)
    print('DISPLAY RESUMED: observe for 35 seconds; original firmware restoration follows.',flush=True)
    phase('resumed',durations[2])
    return rows
