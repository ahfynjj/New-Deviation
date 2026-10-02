import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import rf_session as r

class RfRecoveryTests(unittest.TestCase):
    def test_capture_clocks_gpio_before_read_and_restores_clock(self):
        regs={a:0 for a in r.CAPTURE_ADDRS}
        def read(a):
            if a==r.BODR and not regs[r.AHB4]&2:return 0xffffffff
            return regs[a]
        saved=r.capture(read,regs.__setitem__)
        self.assertEqual(saved[r.BODR],0)
        self.assertEqual(regs[r.AHB4],0)

    def test_capture_cleanup_failure_is_distinct(self):
        regs={a:0 for a in r.CAPTURE_ADDRS}
        def write(a,v):
            if a==r.AHB4 and v==0:return
            regs[a]=v
        with self.assertRaises(r.RfCaptureRecoveryError):r.capture(regs.__getitem__,write)
    def test_reject_live_uart_and_active_irq(self):
        for address in (r.ENABLE,r.RESET,r.ISER,r.ISPR,r.IABR):
            regs={a:0 for a in r.CAPTURE_ADDRS}
            regs[address]=32 if address in (r.ENABLE,r.RESET) else 128
            with self.assertRaises(RuntimeError): r.capture(regs.__getitem__,regs.__setitem__)

    def test_stop_reset_clock_priority_and_power(self):
        regs={a:0 for a in r.CAPTURE_ADDRS};regs[r.PRIORITY]=0x12345678
        saved=r.capture(regs.__getitem__,regs.__setitem__)
        regs.update({r.ENABLE:32,r.ISER:128,r.ISPR:128,r.CR1:0x2d,r.BODR:1<<13})
        writes=[]
        def write(a,v):
            writes.append((a,v))
            if a==r.ICER: regs[r.ISER]&=~v
            elif a==r.ICPR: regs[r.ISPR]&=~v
            elif a==r.BSET: regs[r.BODR]=(regs[r.BODR]|(v&65535))&~(v>>16)
            else: regs[a]=v
        r.restore(regs.__getitem__,write,saved)
        self.assertFalse(regs[r.ISER]&128 or regs[r.ISPR]&128 or regs[r.BODR]&(1<<13))
        self.assertEqual(regs[r.CR1],0)
        for a in (r.ENABLE,r.RESET,r.PRIORITY):self.assertEqual(regs[a],saved[a])
        self.assertLess(writes.index((r.ICER,128)),writes.index((r.CR1,0)))

    def test_failed_disable_or_reset_blocks_resume(self):
        regs={a:0 for a in r.CAPTURE_ADDRS};saved=r.capture(regs.__getitem__,regs.__setitem__)
        regs[r.ISER]=128
        with self.assertRaises(RuntimeError):r.restore(regs.__getitem__,lambda a,v:None,saved)
