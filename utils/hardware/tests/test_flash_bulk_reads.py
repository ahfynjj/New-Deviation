import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from swd_flash import MemAPIO,Q

class DP:
    def __init__(self):
        self.csw=0x03000012;self.tar=0;self.addresses=[];self.bursts=[];self.fail=False
    def write_ap(self,a,v):
        if a==0:self.csw=v
        elif a==4:self.tar=v
        else:raise AssertionError('Bulk reading must never write DRW')
    def read_ap_multiple(self,a,count):
        self.assert_drw(a);self.bursts.append(count)
        if self.fail:raise RuntimeError('USB read failed')
        result=[]
        for _ in range(count):
            self.addresses.append(self.tar);result.append(self.tar)
            if self.csw&0x10:self.tar=(self.tar&~1023)|((self.tar+4)&1023)
        return result
    def assert_drw(self,a):
        if a!=12:raise AssertionError('Only read DRW')
    def flush(self):pass

class BulkTests(unittest.TestCase):
    def test_real_backend_bulk_sfdp_and_non_word_tail_match_reference(self):
        from test_swd_flash import Registers
        from swd_flash import SWDFlash
        class RegisterDP(DP):
            def read_ap_multiple(self,a,count):
                self.assert_drw(a);words=[]
                for _ in range(count):
                    words.append(registers.read32(self.tar))
                    if self.csw&0x10:self.tar=(self.tar&~1023)|((self.tar+4)&1023)
                return words
        registers=Registers();dp=RegisterDP();backend=SWDFlash(MemAPIO(registers,dp,read_only=True))
        observed=backend.check_device()
        self.assertTrue(observed['conservative_status_clear'])
        self.assertEqual(backend.read_external(0,65),b'X'*65)
        self.assertEqual(backend.read_internal(0x08000000,1040),b'I'*1040)
        self.assertEqual(dp.csw,0x03000012)
        self.assertFalse(any(a==Q+20 and v&255 in (6,2,0x20) for a,v in registers.log))
    def test_fifo_which_stalls_at_30_bytes_does_not_wait_for_32(self):
        from test_swd_flash import Registers
        from swd_flash import SWDFlash
        class LimitedFIFO(Registers):
            def read32(self,a):
                if a==Q+8:return 2|(min(30,len(self.fifo))<<8)
                return super().read32(a)
        registers=LimitedFIFO();backend=SWDFlash(MemAPIO(registers,registers))
        backend.check_device()
        self.assertEqual(backend.read_external(0,256),b'X'*256)
    def test_internal_read_splits_at_tar_wrap_without_skips(self):
        dp=DP();io=MemAPIO(None,dp)
        raw=io.read_internal_bytes(0x080003f0,1056)
        expected=list(range(0x080003f0,0x080003f0+1056,4))
        self.assertEqual(dp.addresses,expected)
        self.assertEqual(list(struct.unpack('<264I',raw)),expected)
        self.assertTrue(all(n<=128 for n in dp.bursts))
    def test_internal_bulk_range_rejects_other_memory_and_alignment(self):
        dp=DP();io=MemAPIO(None,dp)
        for a,n in ((0x90000000,32),(0x0801fff0,32),(0x08000001,32),(0x08000000,3)):
            with self.assertRaises(ValueError):io.read_internal_bytes(a,n)
        self.assertFalse(dp.addresses)
    def test_fifo_reads_repeat_fixed_dr_address_and_restore_increment(self):
        dp=DP();io=MemAPIO(None,dp)
        self.assertEqual(io.read_fifo_words(4),[Q+32]*4)
        self.assertEqual(dp.addresses,[Q+32]*4)
        self.assertEqual(dp.csw,0x03000012)
        for n in (0,5):
            with self.assertRaises(ValueError):io.read_fifo_words(n)
    def test_fifo_fault_restores_increment_and_never_retries_consumed_data(self):
        dp=DP();dp.fail=True;io=MemAPIO(None,dp)
        with self.assertRaisesRegex(RuntimeError,'USB read failed'):io.read_fifo_words(4)
        self.assertEqual(dp.csw,0x03000012)
        self.assertEqual(dp.bursts,[4])

if __name__=='__main__':unittest.main()
