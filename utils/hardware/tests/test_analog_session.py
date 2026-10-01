import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import analog_session as a
class RecoveryTests(unittest.TestCase):
 def test_reject_active_adc(self):
  with self.assertRaises(RuntimeError): a.capture(lambda addr:a.BIT)
 def test_restore_adc_without_changing_other_clocks(self):
  regs={a.ENABLE:0x103,a.RESET:0x100}; saved=a.capture(regs.__getitem__)
  regs[a.ENABLE]|=a.BIT
  writes=[]
  def write(addr,value): writes.append((addr,value));regs[addr]=value
  a.restore(regs.__getitem__,write,saved)
  self.assertEqual(regs,saved)
  self.assertIn((a.RESET,0x100|a.BIT),writes)
 def test_failed_reset_blocks_resume(self):
  regs={a.ENABLE:0,a.RESET:0};saved=a.capture(regs.__getitem__)
  with self.assertRaises(RuntimeError):a.restore(regs.__getitem__,lambda addr,value:None,saved)
