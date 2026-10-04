"""Reset-catch/RAM environment independent of installed Flash vectors/code.

No erase/program operations. Never restores or executes a captured old PC.
All exits leave CPU halted; caller/user owns the eventual battery power cycle.
"""
import struct
import time
import boot_chain
import boot_session
import flash_info_bundle
from pll_clock import capture_reset_clock
from swd_flash import MemAPIO,SWDFlash

DHCSR,DCRSR,DCRDR=0xe000edf0,0xe000edf4,0xe000edf8
UID_BASE=0x1ff1e800
CONTROLS={DHCSR,DCRSR,DCRDR,0xe000edfc,0xe000ed08,0xe000e010,0xe000e014,0xe000e018,
    0xe000ed04,0x5c001034,0x5c001054,0x580244e0,0x58021c18,0x58021c00,0x58021c04,
    0x58021c0c,0x58020000,0x5802000c,0x5802480c,0x52002000}

def write_allowed(address,image_bytes):
    return address%4==0 and (address in CONTROLS or 0x24000000<=address<=0x24000000+image_bytes-4
                            or 0x2400e000<=address<=0x2400e07c)

class RecoveryContext:
    def __init__(self,session=None,ap=None,io=None,wait=300,ready_gate=None):
        self.session=session;self.ap=ap;self.io=io;self.wait=wait;self.image_bytes=0
        self.ready_gate=ready_gate
        self.report={'original_firmware_executed':None,'cpu_resume_allowed':False,'writes':[]}
    def _write(self,a,v):
        if not write_allowed(a,self.image_bytes):raise ValueError('Recovery initializer write refused '+hex(a))
        self.report['writes'].append([hex(a),hex(v)])
        self.io.write32(a,v);self.io.flush()
    def _wait(self,predicate,seconds):
        deadline=time.monotonic()+seconds
        while not predicate():
            if time.monotonic()>deadline:raise TimeoutError('Recovery entry timeout; no automatic resume')
            time.sleep(0.02)
    def _core(self,number,value):
        if number not in (15,16,17,18,20) or not self.io.read32(DHCSR)&0x20000:raise RuntimeError('Unsafe RAM core setup')
        self._write(DCRDR,value);self._write(DCRSR,number|0x10000)
        self._wait(lambda:self.io.read32(DHCSR)&0x10000,0.5)
    def finalize_supply(self):
        value=self.io.read32(0x5802480c)
        if value&3!=2:raise RuntimeError('Unsupported supply: never switch bypass/LDO mode')
        if value&4:self._write(0x5802480c,value&~4)
        self._wait(lambda:self.io.read32(0x5802480c)&7==2 and self.io.read32(0x58024804)&0x2000,2)
        latency=self.io.read32(0x52002000)&15
        if latency>7:raise RuntimeError('Unexpected reset Flash latency')
        if latency<2:self._write(0x52002000,(self.io.read32(0x52002000)&~15)|2)
        if self.io.read32(0x52002000)&15<2:raise RuntimeError('Flash latency setup failed')
    def enter(self,kit):
        if not callable(self.ready_gate):raise RuntimeError('Explicit power-held confirmation gate required')
        self.image_bytes=len(kit.reader)
        probe=self.session.probe
        from pyocd.probe.debug_probe import DebugProbe
        # PWLINK2's first port selection releases NRST. Do it BEFORE asserting
        # reset; DebugPort.connect sees an already selected wire protocol.
        probe.connect(DebugProbe.Protocol.SWD)
        probe.assert_reset(True)
        if not probe.is_reset_asserted():raise RuntimeError('NRST assertion failed')
        print('ARMED UNDER RESET: hold POWER; confirm HELD; keep holding until RELEASE message.',flush=True)
        self.ready_gate() # Accessible AP is NOT proof user is holding POWER.
        self.report['power_held_confirmation']=True
        dp=self.session.target.dp
        last=None;deadline=time.monotonic()+self.wait
        while time.monotonic()<deadline:
            try:
                from pyocd.coresight.minimal_mem_ap import MinimalMemAP
                dp.connect(DebugProbe.Protocol.SWD)
                self.ap=MinimalMemAP(dp);self.ap.init();self.io=MemAPIO(self.ap,dp,read_only=False)
                cpuid=self.io.read32(0xe000ed00)
                if cpuid!=0x411fc271:raise ValueError('Unexpected core')
                break
            except ValueError:raise
            except Exception as exc:last=exc;time.sleep(0.05)
        else:raise TimeoutError('No powered MCU under reset: '+str(last))
        self.report['reset_before_catch']=probe.is_reset_asserted()
        self.report['debug_before_catch']={hex(a):hex(self.io.read32(a)) for a in (0xe000edfc,DHCSR)}
        if not self.report['reset_before_catch']:
            raise RuntimeError('NRST no longer asserted after SWD connect; no reset catch armed')
        self._write(0xe000edfc,1) # VC_CORERESET: do not depend on valid Flash vectors.
        self._write(DHCSR,0xa05f0001)
        self.report['debug_armed']={hex(a):hex(self.io.read32(a)) for a in (0xe000edfc,DHCSR)}
        if not self.io.read32(0xe000edfc)&1 or not self.io.read32(DHCSR)&1:
            raise RuntimeError('Reset catch/debug enable did not read back')
        probe.assert_reset(False)
        try:self._wait(lambda:self.io.read32(DHCSR)&0x20000,0.5)
        finally:self.report['debug_after_reset']={hex(a):hex(self.io.read32(a)) for a in (0xe000edfc,DHCSR,0xe000ed04,0xe000ed08)}
        self.report['original_firmware_executed']=False
        # System/Flash identity space is not accessible during NRST on H750.
        # Only core debug controls are touched before the caught halt.
        if self.io.read32(0x5c001000)&0xfff!=0x450 or self.io.read32(0x1ff1e880)&0xffff!=128:
            raise RuntimeError('Not the reviewed H750 device')
        uid=b''.join(struct.pack('<I',self.io.read32(UID_BASE+i)) for i in (0,4,8)).hex()
        if uid!=kit.uid:raise RuntimeError('MCU UID differs from frozen kit; no RAM/Flash load')
        self.report['uid_verified']=True
        # Preload latch before output mode; user is still holding POWER.
        self._write(0x580244e0,self.io.read32(0x580244e0)|0x81)
        self._write(0x58021c18,0x1000)
        self._write(0x58021c04,self.io.read32(0x58021c04)&~0x1000)
        self._write(0x58021c0c,self.io.read32(0x58021c0c)&~(3<<24))
        self._write(0x58021c00,(self.io.read32(0x58021c00)&~(3<<24))|(1<<24))
        if not self.io.read32(0x58021c10)&0x1000:raise RuntimeError('PH12 power hold failed')
        self._write(0x5802000c,(self.io.read32(0x5802000c)&~(3<<8))|(1<<8))
        self._write(0x58020000,self.io.read32(0x58020000)&~(3<<8))
        self._write(0x5c001034,self.io.read32(0x5c001034)|(1<<6))
        self._write(0x5c001054,self.io.read32(0x5c001054)|(1<<18))
        print('HALTED, PH12 HIGH: RELEASE POWER NOW.',flush=True)
        self._wait(lambda:self.io.read32(0x58020010)&0x10,120)
        capture_reset_clock(self.io.read32)
        if self.io.read32(0xe000ed04)&511 or self.io.read32(0xe000ed94)&1 or self.io.read32(0xe000ed14)&0x30000:
            raise RuntimeError('Not reset/thread/cache-clean; no RAM execution')
        if not self.io.read32(0x5200201c)&0x10:raise RuntimeError('Hardware IWDG start unsupported')
        if self.io.read32(0xe000e010)&7 or self.io.read32(0xe000ed28) or self.io.read32(0xe000ed2c):
            raise RuntimeError('Fault/SysTick not reset clean')
        self.finalize_supply() # Finalize Run* BEFORE first AXI RAM write.
        for offset in range(0,len(kit.reader),4):self._write(0x24000000+offset,struct.unpack_from('<I',kit.reader,offset)[0])
        if self._bytes(0x24000000,len(kit.reader))!=kit.reader:raise RuntimeError('RAM reader readback mismatch')
        for address in range(0x2400e000,0x2400e080,4):self._write(address,0)
        if self._bytes(0x2400e000,128)!=bytes(128):raise RuntimeError('Mailbox clear failed')
        self._core(20,1);self._core(16,0x1000000);self._core(17,0x24010000);self._core(18,0x24010000);self._core(15,kit.entry)
        self._write(DHCSR,0xa05f0001)
        self._wait(lambda:self.io.read32(0x2400e000)==0x4e445631 and self.io.read32(0x2400e008) not in (0,1,2),20)
        first=boot_session.decode(self._bytes(0x2400e000,128))
        if first['state']!=3 or first['error']:raise RuntimeError('Recovery RAM initialization failed: '+str(first))
        time.sleep(0.2)
        second=boot_session.decode(self._bytes(0x2400e000,128))
        if not boot_session.is_live(second,first):raise RuntimeError('Recovery RAM loop not advancing')
        boot_chain.quiesce_thread(self.io.read32,self._write,self._core,
            lambda:self._wait(lambda:self.io.read32(DHCSR)&0x20000,0.5),time.sleep)
        qspi=self._bytes(flash_info_bundle.QSPI_ADDR,72)
        result,jedec=struct.unpack_from('<II',qspi)
        if result or jedec!=0xc84018:raise RuntimeError('Recovery RAM QSPI read failed')
        observation=flash_info_bundle.decode(self._bytes(flash_info_bundle.INFO_ADDR,flash_info_bundle.REPORT_BYTES),jedec)
        if not observation['conservative_status_clear']:raise RuntimeError('Flash protected/busy')
        self.report.update(first=first,second=second,observation=observation,ram_readback_verified=True,
                           power_hold_verified=True,halted_in_thread=True)
        print('RECOVERY RAM READY; CPU HALTED. No original Flash code executed.',flush=True)
        return observation
    def _bytes(self,a,n):return b''.join(struct.pack('<I',self.io.read32(p)) for p in range(a,a+n,4))
    def backend(self,journal=None,read_only=True):
        return SWDFlash(MemAPIO(self.ap,self.session.target.dp,read_only=read_only),journal)
    def hold(self):
        self.report['halt_verified']=False
        if self.io is not None:
            # No reset/restore/resume on any outcome, including pending writes.
            self.io.write32(DHCSR,0xa05f0003);self.io.flush()
            if self.io.read32(DHCSR)&0xa0000!=0x20000:raise RuntimeError('CPU halt could not be confirmed; manual recovery required')
            self.io.write32(0xe000edfc,0);self.io.flush() # Only clear catch after halt confirmed.
            self.report['halt_verified']=True
    def close(self):
        if self.session is not None:self.session.close()
