import sys
import unittest
import struct
from types import SimpleNamespace
from unittest.mock import Mock,patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from recovery_context import RecoveryContext,write_allowed
import recovery_context as c
import flash_info_bundle
from probe_report import FIELDS

ROOT=Path(__file__).resolve().parents[3]
UID='010000000200000003000000'

class ResetRAM:
    """No installed firmware/vectors; only emulates AP transfers and RAM reader."""
    def __init__(self,uid=UID):
        self.regs={0xe000ed00:0x411fc271,0x5c001000:0x20036450,0x1ff1e880:128,
            c.DHCSR:0x30003,0x58024400:0x4025,0x5802480c:0x5000046,
            0x58024804:0x6000,0x5200201c:0x1bc6aaf0,0x58020010:0x10}
        self.regs.update({c.UID_BASE+i:int.from_bytes(bytes.fromhex(uid)[i:i+4],'little') for i in (0,4,8)})
        self.core={15:0xfffffffe,17:0xffffffff};self.writes=[];self.sampling=0;self.started=False
    def init(self):pass
    def read32(self,a):
        if 0x08000000<=a<0x08020000:raise AssertionError('Bootstrap must not trust/read installed vectors')
        if a==0x2400e02c and self.started:
            self.sampling+=1;return 100+self.sampling
        if a==0x2400e030 and self.started:return 500+self.sampling*100
        return self.regs.get(a,0)
    def write32(self,a,v):
        self.writes.append((a,v));self.regs[a]=v
        if a==c.DCRSR and v&0x10000:self.core[v&31]=self.regs[c.DCRDR]
        if a==0x58021c18:self.regs[0x58021c14]=self.regs[0x58021c10]=v
        if a==c.DHCSR:
            self.regs[a]=0x30003 if v&2 else 0x1010001
            if not v&2 and self.core[15]==0x240002c1:
                self.started=True
                values=dict(magic=0x4e445631,version=8,state=3,cpuid=0x411fc271,
                    device_id=0x20036450,rcc_cr=0x3030005,rcc_cfgr=0x1b,rcc_d1cfgr=0x48,reserved=15)
                raw=struct.pack('<32I',*[values.get(name,0) for name in FIELDS],*([0]*12))
                for off in range(0,128,4):self.regs[0x2400e000+off]=int.from_bytes(raw[off:off+4],'little')
                sfdp=(ROOT/'docs/tx15/evidence/2026-10-04/flash-info/sfdp.bin').read_bytes()
                info=struct.pack('<II',0x46494e31,0)+bytes.fromhex('00022000')+sfdp
                qspi=struct.pack('<II',0,0xc84018)+b'?'*64
                for base,data in ((flash_info_bundle.INFO_ADDR,info),(flash_info_bundle.QSPI_ADDR,qspi)):
                    for off in range(0,len(data),4):self.regs[base+off]=int.from_bytes(data[off:off+4],'little')

def model_context(model):
    session=Mock()
    session.probe.is_reset_asserted.return_value=True
    session.probe.assert_reset=Mock(side_effect=lambda value:model.regs.update({c.DHCSR:0x30003}) if not value else None)
    return RecoveryContext(session,ready_gate=lambda:None),session

class ContextTests(unittest.TestCase):
    def test_system_identity_reads_wait_for_reset_release_and_caught_halt(self):
        model=ResetRAM();context,session=model_context(model)
        pins={'reset':False}
        original_read=model.read32
        def read(a):
            if pins['reset'] and not 0xe000e000<=a<0xe0010000:
                raise RuntimeError('System bus unavailable while NRST held')
            return original_read(a)
        model.read32=read
        def reset_pin(value):
            pins['reset']=value
            if not value:model.regs[c.DHCSR]=0x30003
        session.probe.assert_reset.side_effect=reset_pin
        session.probe.is_reset_asserted.side_effect=lambda:pins['reset']
        reader=(ROOT/'local/tx15-hardware/flash-info/flash-info.bin').read_bytes()
        with patch('pyocd.coresight.minimal_mem_ap.MinimalMemAP',return_value=model),patch.object(c.time,'sleep'):
            context.enter(SimpleNamespace(reader=reader,entry=0x240002c1,uid=UID))
        self.assertTrue(context.report['uid_verified'])
    def test_probe_port_selection_precedes_nrst_and_dp_connect_cannot_release_it(self):
        model=ResetRAM();context,session=model_context(model)
        pins={'reset':False,'connected':False}
        def connect_port(*args):pins.update(reset=False,connected=True)
        def reset_pin(value):
            pins['reset']=value
            if not value:model.regs[c.DHCSR]=0x30003
        session.probe.connect.side_effect=connect_port
        session.probe.assert_reset.side_effect=reset_pin
        session.probe.is_reset_asserted.side_effect=lambda:pins['reset']
        session.target.dp.connect.side_effect=lambda *args:None if pins['connected'] else connect_port()
        reader=(ROOT/'local/tx15-hardware/flash-info/flash-info.bin').read_bytes()
        with patch('pyocd.coresight.minimal_mem_ap.MinimalMemAP',return_value=model),patch.object(c.time,'sleep'):
            context.enter(SimpleNamespace(reader=reader,entry=0x240002c1,uid=UID))
        self.assertTrue(context.report['reset_before_catch'])
        self.assertFalse(context.report['original_firmware_executed'])
        session.probe.connect.assert_called_once()
    def test_swd_connect_releasing_reset_is_detected_before_catch_or_ram_write(self):
        model=ResetRAM();context,session=model_context(model)
        session.probe.is_reset_asserted.side_effect=[True,False]
        reader=(ROOT/'local/tx15-hardware/flash-info/flash-info.bin').read_bytes()
        with patch('pyocd.coresight.minimal_mem_ap.MinimalMemAP',return_value=model):
            with self.assertRaisesRegex(RuntimeError,'NRST no longer asserted'):
                context.enter(SimpleNamespace(reader=reader,entry=0x240002c1,uid=UID))
        self.assertFalse(model.writes)
        self.assertFalse(context.report['reset_before_catch'])
        self.assertIsNone(context.report['original_firmware_executed'])
    def test_no_gate_or_failed_confirmation_never_releases_reset_or_accesses_ap(self):
        reader=(ROOT/'local/tx15-hardware/flash-info/flash-info.bin').read_bytes()
        kit=SimpleNamespace(reader=reader,entry=0x240002c1,uid=UID)
        model=ResetRAM();context,session=model_context(model)
        context.ready_gate=None
        with self.assertRaises(RuntimeError):context.enter(kit)
        session.probe.assert_reset.assert_not_called()
        context.ready_gate=Mock(side_effect=TimeoutError('No human confirmation'))
        with self.assertRaises(TimeoutError):context.enter(kit)
        self.assertEqual(session.probe.assert_reset.call_args_list[-1].args,(True,))
        session.target.dp.connect.assert_not_called()
        self.assertFalse(model.writes)
    def test_entry_with_invalid_flash_vectors_finalizes_supply_before_ram_and_stays_halted(self):
        model=ResetRAM();context,session=model_context(model)
        reader=(ROOT/'local/tx15-hardware/flash-info/flash-info.bin').read_bytes()
        kit=SimpleNamespace(reader=reader,entry=0x240002c1,uid=UID)
        with patch('pyocd.coresight.minimal_mem_ap.MinimalMemAP',return_value=model),patch.object(c.time,'sleep'):
            observed=context.enter(kit)
        self.assertTrue(observed['conservative_status_clear'])
        supply=next(i for i,(a,v) in enumerate(model.writes) if a==0x5802480c)
        ram=next(i for i,(a,v) in enumerate(model.writes) if a==0x24000000)
        self.assertLess(supply,ram)
        self.assertEqual(model.regs[c.DHCSR]&0x20000,0x20000)
        self.assertFalse(context.report['original_firmware_executed'])
        self.assertEqual(model.core[15],kit.entry)
        self.assertEqual(session.probe.assert_reset.call_args_list[0].args,(True,))
    def test_wrong_uid_rejected_before_any_ram_load(self):
        model=ResetRAM('040000000500000006000000');context,_=model_context(model)
        reader=(ROOT/'local/tx15-hardware/flash-info/flash-info.bin').read_bytes()
        with patch('pyocd.coresight.minimal_mem_ap.MinimalMemAP',return_value=model):
            with self.assertRaises(RuntimeError):context.enter(SimpleNamespace(reader=reader,entry=0x240002c1,uid=UID))
        self.assertEqual(model.writes,[(0xe000edfc,1),(c.DHCSR,0xa05f0001)])
    def test_bootstrap_allowlist_excludes_flash_commands_options_and_sdram(self):
        for addr in (0x08000000,0x90000000,0xd0000000,0x52002004,0x5200200c,0x52002018,0x52005020):
            self.assertFalse(write_allowed(addr,3816),hex(addr))
        for addr in (0x24000000,0x24000ee4,0xe000edf0,0x5802480c,0x52002000):
            self.assertTrue(write_allowed(addr,3816),hex(addr))
        self.assertFalse(write_allowed(0x24000ee8,3816))
        self.assertFalse(write_allowed(0x24000001,3816))
    def test_hold_never_resumes_or_resets_even_after_interruption(self):
        class IO:
            writes=[]
            def read32(self,a):return 0x20000
            def write32(self,a,v):self.writes.append((a,v))
            def flush(self):pass
        io=IO();c=RecoveryContext(None,None,io)
        c.hold()
        self.assertEqual(io.writes,[(0xe000edf0,0xa05f0003),(0xe000edfc,0)])
    def test_cleanup_before_ap_acquired_does_not_claim_halted_or_release_reset(self):
        context=RecoveryContext(session=Mock())
        context.session.probe.assert_reset=Mock()
        context.hold()
        self.assertFalse(context.report['halt_verified'])
        context.session.probe.assert_reset.assert_not_called()
        self.assertFalse(context.report['writes'])
    def test_unfinalized_or_bypass_supply_prevents_all_ram_writes(self):
        class IO:
            def read32(self,a):return 1 if a==0x5802480c else 0
            def write32(self,*args):raise AssertionError('unexpected write')
        c=RecoveryContext(None,None,IO())
        with self.assertRaises(RuntimeError):c.finalize_supply()
    def test_unconfirmed_halt_retains_reset_catch_and_never_claims_halted(self):
        class IO:
            def __init__(self):self.writes=[]
            def read32(self,a):return 0
            def write32(self,a,v):self.writes.append((a,v))
            def flush(self):pass
        io=IO();context=RecoveryContext(None,None,io)
        with self.assertRaises(RuntimeError):context.hold()
        self.assertFalse(context.report['halt_verified'])
        self.assertEqual(io.writes,[(0xe000edf0,0xa05f0003)])

if __name__=='__main__':unittest.main()
