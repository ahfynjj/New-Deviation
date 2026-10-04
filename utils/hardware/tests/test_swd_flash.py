"""Controller emulation checks; these do not prove physical programming."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import swd_flash as f
import flash_journal as j
from flash_transaction import Transaction

SFDP=(Path(__file__).resolve().parents[3]/'docs/tx15/evidence/2026-10-04/flash-info/sfdp.bin').read_bytes()

class Registers:
    def __init__(self):
        self.regs=dict(f.REQUIRED)
        self.regs.update({f.AHB3:0, f.Q:0,f.Q+4:0,f.Q+20:0,f.Q+8:0,
            f.F:0x37,f.F+12:0x31,f.F+16:0,f.F+24:1,f.F+28:0x1bc6aaf0,
            f.F+40:0xff,f.F+48:0xff,f.F+56:0xff})
        self.ext=bytearray(b'X'*1048576);self.internal=bytearray(b'I'*131072)
        self.log=[];self.fifo=b'';self.pending=None;self.status=bytearray([0,2,0x20]);self.buffer=b''
    def read32(self,a):
        if a==f.Q+8:return 2|(min(32,len(self.fifo))<<8)
        if a==f.Q+32:
            data=self.fifo[:4];self.fifo=self.fifo[4:]
            return int.from_bytes(data.ljust(4,b'\0'),'little')
        if 0x08000000<=a<0x08020000:return int.from_bytes(self.internal[a-0x08000000:a-0x08000000+4],'little')
        return self.regs.get(a,0)
    def write32(self,a,v):
        self.log.append((a,v));self.regs[a]=v
        if a==f.Q+20:
            op=v&255;self.pending=op
            if op==6:self.status[0]=2
            if op in (5,0x35,0x15):self.fifo=bytes([self.status[(5,0x35,0x15).index(op)]])
            if op==0x9f:self.fifo=bytes.fromhex('c84018')
        if a==f.Q+24:
            n=self.regs[f.Q+16]+1
            if self.pending==0x5a:self.fifo=SFDP[v:v+n]
            if self.pending==3:self.fifo=bytes(self.ext[v:v+n])
            if self.pending==0x20:self.ext[v:v+4096]=b'\xff'*4096;self.status[0]=0
            if self.pending==2:self.buffer=b''
        if a==f.Q+32:
            self.buffer+=v.to_bytes(4,'little')
            if len(self.buffer)==256:
                off=self.regs[f.Q+24];self.ext[off:off+256]=self.buffer;self.status[0]=0
        if a==f.F+4 and v==0xcdef89ab:self.regs[f.F+12]&=~1
        if a==f.F+12 and v&0x80:self.internal[:]=b'\xff'*131072
        if 0x08000000<=a<0x08020000:self.internal[a-0x08000000:a-0x08000000+4]=v.to_bytes(4,'little')
    def flush(self):pass

class BackendTests(unittest.TestCase):
    def setUp(self):self.io=Registers();self.backend=f.SWDFlash(self.io)
    def test_read_only_check_no_write_enable_or_unlock(self):
        info=self.backend.check_device()
        self.assertTrue(info['conservative_status_clear'])
        self.assertEqual(self.backend.read_external(0,65),b'X'*65)
        self.assertEqual(self.backend.read_internal(0x08000000,36),b'I'*36)
        self.assertFalse(any(a==f.F+4 or a==f.Q+20 and v&255 in (6,2,0x20) for a,v in self.io.log))
    def test_bad_environment_rejected_before_controller_write(self):
        for address in f.REQUIRED:
            io=Registers();io.regs[address]^=0xffffffff
            with self.subTest(address=hex(address)),self.assertRaises(RuntimeError):f.SWDFlash(io).check_device()
            self.assertEqual(io.log,[])
    def test_protection_or_busy_blocks_before_unlock(self):
        for a,v in [(f.F+28,0),(f.F+56,0xfe),(f.F+40,0),(f.F+48,0),(f.F+16,1)]:
            io=Registers();io.regs[a]=v
            with self.assertRaises(RuntimeError):f.SWDFlash(io).check_device()
            self.assertEqual(io.log,[])
    def test_bounds_and_no_journal_block_mutations(self):
        self.backend.check_device();self.io.log=[]
        for action in [lambda:self.backend.erase_external(1048576,4096),
                       lambda:self.backend.program_external(1,b'A'*256),
                       lambda:self.backend.erase_internal(0x08020000,131072),
                       lambda:self.backend.program_internal(0x08000004,b'B'*32),
                       lambda:self.backend.erase_external(0,4096)]:
            with self.assertRaises((ValueError,RuntimeError)):action()
        self.assertEqual(self.io.log,[])
    def test_journal_precedes_wren_and_key_and_exact_program_units(self):
        plan=Transaction(b'B'*64,b'A'*512,bytes(self.io.internal),bytes(self.io.ext))
        with tempfile.TemporaryDirectory() as folder:
            journal=j.Journal.create(Path(folder)/'journal.json',plan,'install',plan.seal)
            b=f.SWDFlash(self.io,journal);b.check_device()
            original_write=self.io.write32
            def guarded(a,v):
                if a==f.F+4 or a==f.Q+20 and v&255 in (6,2,0x20):
                    record=j.Journal.read(journal.path)
                    self.assertTrue(record['original_resume_forbidden'])
                    self.assertIn(record['state'],('intent','command-complete'))
                original_write(a,v)
            self.io.write32=guarded
            b.erase_external(0,4096);b.program_external(0,plan.payload[:256])
            b.verified_stage('external')
            b.erase_internal(0x08000000,131072);b.program_internal(0x08000000,plan.boot[:32])
            self.assertEqual(b.read_external(0,256),b'A'*256)
            self.assertEqual(b.read_internal(0x08000000,32),b'B'*32)
            self.assertTrue(self.io.regs[f.F+12]&1)
            self.assertEqual(j.Journal.read(journal.path)['sequence'],4)
    def test_journal_storage_failure_prevents_target_mutation(self):
        class Broken:
            def before(self,*args):raise OSError('disk full')
        b=f.SWDFlash(self.io,Broken());b.check_device();self.io.log=[]
        with self.assertRaises(OSError):b.erase_external(0,4096)
        self.assertEqual(self.io.log,[])
    def test_internal_errors_and_qspi_errors_abort(self):
        self.io.regs[f.F+16]=1<<18
        with self.assertRaises(RuntimeError):self.backend.check_device()
        self.io=Registers();original=self.io.read32
        self.io.read32=lambda a:0x10 if a==f.Q+8 else original(a)
        with self.assertRaises(RuntimeError):f.SWDFlash(self.io).check_device()
    def test_timeout_never_locks_or_resumes_pending_internal_erase(self):
        plan=Transaction(b'B'*64,b'A'*512,bytes(self.io.internal),bytes(self.io.ext))
        with tempfile.TemporaryDirectory() as folder:
            journal=j.Journal.create(Path(folder)/'journal.json',plan,'install',plan.seal)
            b=f.SWDFlash(self.io,journal);b.check_device()
            b.erase_external(0,4096);b.verified_stage('external')
            original_write=self.io.write32
            def busy(a,v):
                original_write(a,v)
                if a==f.F+12 and v==0xb4:self.io.regs[f.F+16]=4
            self.io.write32=busy
            now=[0]
            def clock():now[0]+=60;return now[0]
            b.clock=clock;self.io.log=[]
            with self.assertRaises(TimeoutError):b.erase_internal(0x08000000,131072)
            self.assertNotIn((f.F+12,0x31),self.io.log)
            self.assertFalse(any(a==0xe000edf0 for a,v in self.io.log))
            self.assertEqual(j.Journal.read(journal.path)['state'],'intent')
    def test_nor_wel_failure_no_erase_and_pending_intent_preserved(self):
        plan=Transaction(b'B'*64,b'A'*512,bytes(self.io.internal),bytes(self.io.ext))
        with tempfile.TemporaryDirectory() as folder:
            journal=j.Journal.create(Path(folder)/'journal.json',plan,'install',plan.seal)
            b=f.SWDFlash(self.io,journal);b.check_device()
            original_write=self.io.write32
            def no_wel(a,v):
                original_write(a,v)
                if a==f.Q+20 and v&255==6:self.io.status[0]=0
            self.io.write32=no_wel;self.io.log=[]
            with self.assertRaises(RuntimeError):b.erase_external(0,4096)
            self.assertFalse(any(a==f.Q+20 and v&255==0x20 for a,v in self.io.log))
            self.assertEqual(j.Journal.read(journal.path)['state'],'intent')
    def test_transport_allowlist_independently_blocks_erase_keys_and_data(self):
        io=f.MemAPIO(self.io,self.io)
        for a,v in [(f.F+4,0x45670123),(f.F+12,0xb4),(0x08000000,0),
                    (f.Q+20,0x106),(f.Q+20,0x2520),(f.Q+32,0),
                    (f.Q+20,0x04000103),(f.AHB3,0x1000)]:
            with self.assertRaises(ValueError):io.write32(a,v)
        self.assertEqual(self.io.log,[])
    def test_read_only_trial_matches_ram_observation_and_two_original_prefixes(self):
        import flash_geometry
        observed=flash_geometry.assess(0xc84018,[0,2,0x20],SFDP)
        report=f.read_only_check(self.io,self.io,observed,b'X'*64,b'I'*64)
        self.assertEqual(report['flash_mutation_commands'],0)
        self.assertEqual(report['backend_check'],'read-only-prefixes-verified')
        self.assertFalse(any(a==f.F+4 or a==f.Q+20 and v&255 in (6,2,0x20) for a,v in self.io.log))
    def test_transaction_and_hardware_backend_use_same_journal_checkpoints(self):
        plan=Transaction(b'B'*64,b'A'*512,bytes(self.io.internal),bytes(self.io.ext))
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'journal.json'
            result=j.execute(plan,lambda journal:f.SWDFlash(self.io,journal),'install',plan.seal,path)
            record=j.Journal.read(path)
            self.assertEqual(result,['external-verified','internal-verified'])
            self.assertEqual(record['state'],'installed')
            self.assertEqual(record['checkpoints'],['external','internal'])
            self.assertTrue(record['original_resume_forbidden'])
            self.assertEqual(bytes(self.io.ext[4096:]),plan.original_external[4096:])

if __name__=='__main__':unittest.main()
