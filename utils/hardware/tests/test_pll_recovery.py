import importlib.util
from pathlib import Path
import unittest


class PllRecoveryTests(unittest.TestCase):
    def test_live_readback_rejects_wrong_pll_and_bus_settings(self):
        path = Path(__file__).resolve().parents[1] / 'pll_clock.py'
        spec = importlib.util.spec_from_file_location('pll_clock', path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        good = {m.CR: 0x3034025, m.CFGR: 0x1b, m.D1: 0x48,
                m.D2: 0x440, m.D3: 0x40, m.SEL: 0x20200c2,
                m.CFG: 0x1f90008, m.DIV: 0x101023f}
        self.assertEqual(m.capture_pll128_clock(good.__getitem__), good)
        for a, v in [(m.CR, 0x1034025), (m.CFGR, 0x12), (m.D1, 0x40),
                     (m.D2, 0x40), (m.D3, 0), (m.SEL, 0xc0),
                     (m.CFG, 0x10000), (m.DIV, 0x23e)]:
            bad = dict(good)
            bad[a] = v
            with self.assertRaises(RuntimeError):
                m.capture_pll128_clock(bad.__getitem__)

    def test_recovery_order_and_timeout_keeps_pll_running(self):
        path = Path(__file__).resolve().parents[1] / 'pll_clock.py'
        self.assertTrue(path.exists())
        spec = importlib.util.spec_from_file_location('pll_clock', path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        for fail in (None, 'switch', 'pll_off', 'restore'):
            saved = {m.CR: 0x4025, m.CFGR: 0, m.D1: 0, m.D2: 0, m.D3: 0,
                     m.SEL: 0x2020200, m.CFG: 0x1ff0000, m.DIV: 0x1010280}
            r = dict(saved)
            r.update({m.CR: 0x3034025, m.CFGR: 0x1b, m.D1: 0x48,
                      m.D2: 0x440, m.D3: 0x40, m.SEL: 0xc2, m.CFG: 0x10008,
                      m.DIV: 0x101023f})
            count = 0
            def read(a):
                nonlocal count
                count += 1
                self.assertLess(count, 150)
                return r[a]
            def write(a, v):
                if a == m.CFGR and (v & 7) == 0 and fail != 'switch':
                    v &= ~0x38
                if a == m.CR and not v & 0x1000000:
                    self.assertEqual(r[m.CFGR] & 0x3f, 0)
                    if fail != 'pll_off':
                        v &= ~0x2000000
                if a in (m.SEL, m.CFG, m.DIV, m.D1, m.D2, m.D3):
                    self.assertEqual(r[m.CR] & 0x3000000, 0)
                    if fail == 'restore' and a == m.D1:
                        return
                if a == m.CR and not v & 0x10000:
                    self.assertEqual(r[m.CR] & 0x3000000, 0)
                    v &= ~0x20000
                r[a] = v
            if fail:
                with self.assertRaises(RuntimeError):
                    m.restore_pll_clock(read, write, saved, budget=4)
            else:
                self.assertEqual(m.restore_pll_clock(read, write, saved, budget=4), saved)
            if fail == 'switch':
                self.assertEqual(r[m.CR] & 0x3000000, 0x3000000)
