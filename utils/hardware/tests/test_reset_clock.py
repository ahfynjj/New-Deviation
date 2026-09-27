"""Recovery must confirm HSI selection before disabling HSE or resuming Flash."""
import importlib.util
from pathlib import Path
import unittest


class ResetClockTests(unittest.TestCase):
    def test_recovery_waits_for_hsi_and_switch_and_fails_closed(self):
        path = Path(__file__).resolve().parents[1] / 'reset_clock.py'
        self.assertTrue(path.exists())
        spec = importlib.util.spec_from_file_location('reset_clock', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for failure in (None, 'hsi', 'switch', 'hse_off'):
            regs = {0x58024400: 0x34025, 0x58024410: 0x12, 0x58024418: 0}
            if failure == 'hsi':
                regs[0x58024400] &= ~4
            writes = []
            polls = 0
            def read(address):
                nonlocal polls
                polls += 1
                self.assertLess(polls, 50)
                return regs[address]
            def write(address, value):
                writes.append((address, value))
                if address == 0x58024410:
                    self.assertEqual(regs[0x58024400] & 5, 5)
                    self.assertEqual(value & 7, 0)
                    if failure != 'switch':
                        value &= ~0x38
                else:
                    self.assertEqual(address, 0x58024400)
                    if not value & 0x10000:
                        self.assertEqual(regs[0x58024410] & 0x3f, 0)
                        if failure != 'hse_off':
                            value &= ~0x20000
                regs[address] = value
            if failure:
                with self.assertRaises(RuntimeError):
                    module.restore_reset_clock(read, write, budget=4)
            else:
                result = module.restore_reset_clock(read, write, budget=4)
                self.assertEqual(result['rcc_cr'], 0x4025)
                self.assertEqual(result['rcc_cfgr'], 0)
            if failure == 'hsi':
                self.assertFalse(any(a == 0x58024410 for a, v in writes))
            if failure == 'switch':
                self.assertTrue(regs[0x58024400] & 0x10000)

    def test_unsupported_states_are_rejected_without_writes(self):
        path = Path(__file__).resolve().parents[1] / 'reset_clock.py'
        spec = importlib.util.spec_from_file_location('reset_clock', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for address, value in [(module.CR, 0x1034025), (module.CR, 0x74025),
                               (module.CR, 0x3402d), (module.D1CFGR, 8),
                               (module.CFGR, 0x1b), (module.CFGR, 0x0a)]:
            regs = {module.CR: 0x34025, module.CFGR: 0x12, module.D1CFGR: 0}
            regs[address] = value
            writes = []
            with self.assertRaises(RuntimeError):
                module.restore_reset_clock(regs.__getitem__, lambda a, v: writes.append((a, v)))
            self.assertEqual(writes, [])

    def test_successful_transitions_may_take_multiple_reads(self):
        path = Path(__file__).resolve().parents[1] / 'reset_clock.py'
        spec = importlib.util.spec_from_file_location('reset_clock', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        regs = {module.CR: 0x34021, module.CFGR: 0x12, module.D1CFGR: 0}
        pending = {}
        def read(address):
            if address in pending:
                pending[address][0] -= 1
                if pending[address][0] == 0:
                    regs[address] = pending.pop(address)[1]
            return regs[address]
        def write(address, value):
            if address == module.CFGR:
                self.assertEqual(regs[module.CR] & 5, 5)
                target = value & ~0x38
            elif value & 0x10000:
                target = value | 4
            else:
                self.assertEqual(regs[module.CFGR] & 0x3f, 0)
                target = value & ~0x20000
            regs[address] = value
            pending[address] = [3, target]
        result = module.restore_reset_clock(read, write, budget=4)
        self.assertEqual(result, {'rcc_cr': 0x4025, 'rcc_cfgr': 0, 'rcc_d1cfgr': 0})
