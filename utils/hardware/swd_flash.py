"""Bounded TX15 H750 SWD controller backend; no device opening/install CLI.

Requires the pinned flash-info RAM initializer, halted in thread mode with
SysTick stopped. check_device and reads never send WREN or FLASH keys.
Mutation additionally requires a durable, image-bound Journal. A seal is not
human permission. The first pinned TX15 install passed physical erase/program
and full readback on 2026-10-04; original-image recovery writing remains untested.

STM32 register definitions: ST stm32h750xx.h, stm32h7xx_hal_flash{,_ex}.c.
NOR commands: GD25Q128H Rev1.2 reference (exact suffix is not identified).
"""
import struct
import time
import flash_geometry

Q=0x52005000
F=0x52002000
AHB3=0x580244d4
ERRORS=sum(1<<bit for bit in (17,18,19,21,22,23,24,25,26))
# Full-width values intentionally match this reviewed initializer, not a generic H7.
REQUIRED={0x5c001000:0x20036450,0x1ff1e880:128,
    0xe000ed04:0,0xe000e010:0,0xe000ed94:0,
    0xe000edf0:0x20000,0xe000ed14:0,0x580244e0:0x80,
    0x58021c00:1<<24,0x58021c14:0x1000,0x58021c10:0x1000,
    0x5802480c:2,0x58024804:0xe000,0x58024818:0xe000,
    0x58024400:0x03030005,0x58024410:0x1b,0x58024418:0x48,
    0x5802441c:0x440,0x58024420:0x40,0x5802444c:0,
    0x58024428:0xc2,0x5802442c:0x00010008,0x58024430:0x23f}
# Mask reserved/unrelated clock and identity fields; all relevant fields checked.
MASKS={0x5c001000:0xfff,0x1ff1e880:0xffff,0xe000ed04:0x1ff,
    0xe000e010:7,0xe000edf0:0xa0000,0xe000ed14:0x30000,
    0x580244e0:0x80,0x58021c00:3<<24,0x58021c14:0x1000,0x58021c10:0x1000,
    0x5802480c:7,0x58024804:0xe000,0x58024818:0xe000,
    0x58024400:0x3f0f001d,0x58024410:0x3f,
    0x58024418:0xf7f,0x5802441c:0x770,0x58024420:0x70,0x5802444c:0x30,
    0x58024428:0x3f3,0x5802442c:0x7000f,0x58024430:0xffff}

class MemAPIO:
    """MinimalMemAP adapter; synchronous stores, no target-driver flash calls."""
    def __init__(self,ap,dp,read_only=True):
        self.ap=ap;self.dp=dp;self.read_only=read_only;self.writes=[]
    def read32(self,address):return self.ap.read32(address)
    def write32(self,address,value):
        if self.read_only:
            allowed={AHB3,Q,Q+4,Q+12,Q+16,Q+20,Q+24}
            if address not in allowed:raise ValueError('Read-only adapter refuses write address')
            if address==AHB3 and value!=self.read32(AHB3)|0x4000:raise ValueError('Read-only QSPI clock enable only')
            if address==Q and value!=0x0f000001 or address==Q+4 and value!=0x00170300:
                raise ValueError('Read-only adapter refuses controller configuration')
            if address==Q+20 and value not in (0x0500019f,0x05000105,0x05000135,0x05000115,0x0520255a,0x05002503):
                raise ValueError('Read-only adapter refuses SPI opcode/mode')
        self.writes.append((address,value))
        self.ap.write32(address,value);self.dp.flush()
    def flush(self):self.dp.flush()
    def read_internal_bytes(self,address,size):
        SWDFlash._range(address,size,0x08000000,0x08020000,4)
        if size%4:raise ValueError('Internal bulk read must be word aligned')
        if not hasattr(self.dp,'read_ap_multiple'):
            return b''.join(struct.pack('<I',self.read32(a)) for a in range(address,address+size,4))
        result=bytearray()
        self.dp.write_ap(0,0x03000012)
        while len(result)<size:
            current=address+len(result)
            count=min(128,(1024-(current&1023))//4,(size-len(result))//4)
            self.dp.write_ap(4,current)
            words=self.dp.read_ap_multiple(12,count)
            if len(words)!=count:raise RuntimeError('Short bulk internal read')
            result.extend(struct.pack('<'+'I'*count,*words))
        return bytes(result)
    def read_fifo_words(self,count):
        if type(count) is not int or not 1<=count<=4:raise ValueError('FIFO burst must fit 16 available bytes')
        if not hasattr(self.dp,'read_ap_multiple'):return [self.read32(Q+32) for _ in range(count)]
        try:
            self.dp.write_ap(0,0x03000002) # No address increment: every read is QSPI DR.
            self.dp.write_ap(4,Q+32)
            words=self.dp.read_ap_multiple(12,count)
            if len(words)!=count:raise RuntimeError('Short FIFO burst; never retry consumed data')
            return words
        finally:
            self.dp.write_ap(0,0x03000012);self.dp.flush()

class SWDFlash:
    def __init__(self,io,journal=None,clock=time.monotonic):
        self.io=io;self.journal=journal;self.clock=clock;self.checked=False
    def _read(self,a):return self.io.read32(a)
    def _write(self,a,v):self.io.write32(a,v);self.io.flush()
    def _until(self,predicate,seconds=2):
        deadline=self.clock()+seconds
        while True:
            value=predicate()
            if value:return value
            if self.clock()>=deadline:raise TimeoutError('Flash controller deadline exceeded; keep CPU halted')
    def _environment(self):
        for address,expected in REQUIRED.items():
            mask=MASKS.get(address,0xffffffff)
            if self._read(address)&mask!=expected&mask:raise RuntimeError('Unexpected device/clock/core register '+hex(address))
        if self._read(0xe000edf0)&0xa0000!=0x20000:raise RuntimeError('CPU not safely halted')
        if self._read(0xe000ed14)&0x30000:raise RuntimeError('Caches must be disabled')
        if self._read(0x580244e0)&0x80==0:raise RuntimeError('GPIOH clock off')
        if self._read(0x58021c00)>>24&3!=1 or not self._read(0x58021c14)&0x1000 or not self._read(0x58021c10)&0x1000:
            raise RuntimeError('PH12 power hold missing')
        if self._read(0x5802480c)&7!=2 or self._read(0x58024804)&0xe000!=0xe000 or self._read(0x58024818)&0xe000!=0xe000:
            raise RuntimeError('LDO/VOS1 not ready')
        if not 2<=self._read(F)&15<=7:raise RuntimeError('Unsafe Flash latency')
        if self._read(0x5802444c)&0x30:raise RuntimeError('Wrong QSPI kernel clock')
        # Never alter option bytes/protection. PRAR/SCAR disabled starts > ends.
        if self._read(F+28)>>8&255!=0xaa or not self._read(F+56)&1:
            raise RuntimeError('Read/write protection enabled')
        for address in (F+40,F+48):
            value=self._read(address)
            if value&0xfff<=value>>16&0xfff:raise RuntimeError('Protected/secure area enabled')
        if self._read(F+16)&(15|ERRORS):raise RuntimeError('Internal Flash busy/error')
        if self._read(F+12)&~0x31:raise RuntimeError('Unexpected internal Flash operation')
    def _qsr(self):
        value=self._read(Q+8)
        if value&0x11:raise RuntimeError('QSPI transfer error; keep CPU halted')
        return value
    def _command(self,opcode,size=0,address=None,write_data=None):
        self._until(lambda:not self._qsr()&0x20)
        self._write(Q+12,0x1b)
        if size:self._write(Q+16,size-1)
        ccr=0x100|opcode
        if address is not None:ccr|=0x2400 # ADMODE single / 24-bit address
        if opcode==0x5a:ccr|=8<<18
        if size:ccr|=1<<24
        if size and write_data is None:ccr|=1<<26
        self._write(Q+20,ccr)
        if address is not None:self._write(Q+24,address)
        result=bytearray()
        offset=0
        while offset<size:
            n=min(4,size-offset)
            if write_data is None and size-offset>=4 and hasattr(self.io,'read_fifo_words'):
                n=min(16,size-offset)//4*4 # TX15 SFDP read can stall at FLEVEL=30.
                self._until(lambda:(self._qsr()>>8&63)>=n)
                words=self.io.read_fifo_words(n//4)
                result+=struct.pack('<'+'I'*(n//4),*words)
            elif write_data is None:
                self._until(lambda:(self._qsr()>>8&63)>=n)
                result+=self._read(Q+32).to_bytes(4,'little')[:n]
            else:
                self._until(lambda:(self._qsr()>>8&63)<=32-n)
                self._write(Q+32,int.from_bytes(write_data[offset:offset+n],'little'))
            offset+=n
        self._until(lambda:self._qsr()&0x22==2)
        self._write(Q+12,0x1b)
        return bytes(result)
    def _status(self):return bytes(self._command(op,1)[0] for op in (5,0x35,0x15))
    def check_device(self):
        self.checked=False;self._environment()
        # The RAM reader stops/reset the controller; permit our own known idle config on recheck.
        self._write(AHB3,self._read(AHB3)|0x4000)
        if self._read(Q) not in (0,0x0f000001) or self._read(Q+4) not in (0,0x00170300) or self._qsr()&0x20:
            raise RuntimeError('QSPI not reset/known-idle')
        self._write(Q+4,0x00170300);self._write(Q,0x0f000001)
        if self._read(Q)!=0x0f000001 or self._read(Q+4)!=0x00170300:raise RuntimeError('QSPI setup readback failed')
        jedec=int.from_bytes(self._command(0x9f,3),'big')
        status=self._status();sfdp=self._command(0x5a,1024,0)
        report=flash_geometry.assess(jedec,status,sfdp)
        if not report['conservative_status_clear']:raise RuntimeError('NOR protected/busy/unknown configuration')
        self.status=status;self.checked=True
        return report
    def _require_checked(self):
        if not self.checked:raise RuntimeError('Fresh device preflight required')
    @staticmethod
    def _range(address,size,start,limit,alignment=1):
        if not isinstance(address,int) or not isinstance(size,int) or size<0 or address%alignment or address<start or size>limit-address:
            raise ValueError('Out-of-range/unaligned Flash operation')
    def read_external(self,offset,size):
        self._range(offset,size,0,1048576);self._require_checked()
        result=bytearray()
        for i in range(0,size,256):
            if size>=65536 and i%65536==0:print(f'READ EXTERNAL {offset+i:#x}: {i}/{size}',flush=True)
            result.extend(self._command(3,min(256,size-i),offset+i))
        return bytes(result)
    def read_internal(self,address,size):
        self._range(address,size,0x08000000,0x08020000,4);self._require_checked()
        if size%4:raise ValueError('Internal read must be word aligned')
        if size>=65536:print(f'READ INTERNAL {address:#x}: {size} bytes',flush=True)
        if hasattr(self.io,'read_internal_bytes'):return self.io.read_internal_bytes(address,size)
        return b''.join(struct.pack('<I',self._read(a)) for a in range(address,address+size,4))
    def _intent(self,op,address,value):
        self._require_checked()
        if self.journal is None:raise RuntimeError('Durable transaction journal required; no mutation')
        self._environment()
        self.journal.before(op,address,value)
    def _nor_write(self,op,address,data=None):
        if self._status()!=self.status:raise RuntimeError('NOR status changed before mutation')
        self._command(6)
        if self._status()!=bytes([2,self.status[1],self.status[2]]):raise RuntimeError('WEL not set exactly')
        self._command(op,len(data) if data is not None else 0,address,data)
        self._until(lambda:not self._command(5,1)[0]&1,10)
        if self._status()!=self.status:raise RuntimeError('NOR did not return to clean original status')
        self.journal.command_complete()
    def erase_external(self,offset,size):
        self._range(offset,size,0,1048576,4096)
        if size!=4096:raise ValueError('Only 4 KiB sector erase permitted')
        self._intent('external-erase',offset,size);self._nor_write(0x20,offset)
    def program_external(self,offset,data):
        self._range(offset,len(data),0,1048576,256)
        if type(data) is not bytes or len(data)!=256:raise ValueError('Only complete 256B page permitted')
        self._intent('external-program',offset,data)
        if self.read_external(offset,256)!=b'\xff'*256:raise RuntimeError('NOR page not erased')
        self._nor_write(2,offset,data)
    def _unlock(self):
        if self._read(F+12)&1:
            self._write(F+4,0x45670123);self._write(F+4,0xcdef89ab)
        if self._read(F+12)&1:raise RuntimeError('Internal Flash unlock failed')
        self._write(F+20,0x10000|ERRORS)
    def _internal_done(self):
        self._until(lambda:not self._read(F+16)&15,50)
        if self._read(F+16)&ERRORS:raise RuntimeError('Internal Flash operation failed')
        # No finally block: a timeout/busy operation must not be reset or resumed.
        self._write(F+12,0x31)
        if self._read(F+12)!=0x31:raise RuntimeError('Internal Flash lock failed')
        self.journal.command_complete()
    def erase_internal(self,address,size):
        if (address,size)!=(0x08000000,131072):raise ValueError('Only H750 bank1 sector0 permitted')
        self._intent('internal-erase',address,size);self._unlock()
        self._write(F+12,0x34);self._write(F+12,0xb4);self._internal_done()
    def program_internal(self,address,data):
        self._range(address,len(data),0x08000000,0x08020000,32)
        if type(data) is not bytes or len(data)!=32:raise ValueError('Only 256-bit internal Flash word permitted')
        self._intent('internal-program',address,data)
        if self.read_internal(address,32)!=b'\xff'*32:raise RuntimeError('Internal word not erased')
        self._unlock();self._write(F+12,0x32)
        for offset in range(0,32,4):self._write(address+offset,struct.unpack_from('<I',data,offset)[0])
        self._internal_done()
    def verified_stage(self,stage):
        if self.journal is None:raise RuntimeError('Journal missing')
        self.journal.checkpoint(stage)

def read_only_check(ap,dp,observed,prefix,internal_prefix):
    """Use a separate transport allowlist; caller owns halt/clock cleanup."""
    io=MemAPIO(ap,dp) # Cannot issue WREN/program/erase/FLASH-key writes.
    backend=SWDFlash(io)
    report=backend.check_device()
    if report!=observed:raise RuntimeError('SWD backend and RAM reader observations differ')
    if backend.read_external(0,len(prefix))!=prefix:raise RuntimeError('SWD NOR prefix differs from backup')
    if backend.read_internal(0x08000000,len(internal_prefix))!=internal_prefix:raise RuntimeError('SWD internal prefix differs from backup')
    report=dict(report,backend_check='read-only-prefixes-verified',
        controller_setup_writes=len(io.writes),flash_mutation_commands=0,
        internal_prefix_bytes=len(internal_prefix),external_prefix_bytes=len(prefix))
    return report
