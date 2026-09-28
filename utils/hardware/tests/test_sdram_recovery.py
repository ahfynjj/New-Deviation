import importlib.util
from pathlib import Path
import unittest

class SdramRecoveryTests(unittest.TestCase):
    def test_capture_cleanup_attempts_both_clocks_and_reports_readback_failure(self):
        path=Path(__file__).resolve().parents[1]/'sdram_session.py'
        spec=importlib.util.spec_from_file_location('sdram_session',path)
        m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        for failure in ('write','readback'):
            regs={a:0 for a in m.GPIO_REGS+m.FMC_REGS+(m.AHB3,m.AHB4,m.RST)}
            regs[m.AHB4]=0x81
            restored=[]
            def write(a,v):
                if a in (m.AHB3,m.AHB4) and v in (0,0x81):
                    restored.append(a)
                    if a==m.AHB3:
                        if failure=='write': raise RuntimeError('injected clock restore failure')
                        return
                regs[a]=v
            with self.assertRaises(m.SdramCaptureRecoveryError):
                m.capture_sdram_reset(regs.__getitem__,write)
            self.assertEqual(restored,[m.AHB3,m.AHB4])
            self.assertEqual(regs[m.AHB4],0x81)

    def test_restore_resets_fmc_before_gpio_and_preserves_power(self):
        path=Path(__file__).resolve().parents[1]/'sdram_session.py'
        self.assertTrue(path.exists())
        spec=importlib.util.spec_from_file_location('sdram_session',path)
        m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        for fail in (False,True):
            regs={a:0 for a in m.GPIO_REGS+m.FMC_REGS+(m.AHB3,m.AHB4,m.RST)}
            regs[m.AHB4]=0x81; regs[0x58021c00]=0xfdffffff
            fmc_reset=False
            def read(a): return regs[a]
            def write(a,v):
                nonlocal fmc_reset
                if a==m.RST and v&0x1000:
                    fmc_reset=True
                    for address in m.FMC_REGS: regs[address]=0
                if a in m.GPIO_REGS:
                    self.assertTrue(fmc_reset)
                    if a==0x58021c00: self.assertEqual(v&0x3000000,0x1000000)
                    if fail and a==0x58020800: return
                regs[a]=v
            saved=m.capture_sdram_reset(read,write)
            for a in m.GPIO_REGS: regs[a]=0xaaaaaaaa
            regs[0x52004000]=0x800030da; regs[m.AHB3]=0x1000; regs[m.AHB4]=0xfd
            if fail:
                with self.assertRaises(RuntimeError): m.restore_sdram_reset(read,write,saved)
            else:
                m.restore_sdram_reset(read,write,saved)
                self.assertEqual({a:read(a) for a in saved},saved)
