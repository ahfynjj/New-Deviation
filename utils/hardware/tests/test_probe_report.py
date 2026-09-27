"""Check debugger evidence; synthetic dumps are not hardware validation."""
import importlib.util
from pathlib import Path
import struct
import unittest

MODULE = Path(__file__).resolve().parents[1] / "probe_report.py"


class ProbeReportTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.exists(), "RAM probe report decoder is not implemented")
        spec = importlib.util.spec_from_file_location("probe_report", MODULE)
        self.report = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.report)

    def dump(self, ticks=10, loops=100, state=3, error=0, version=1, power=0):
        # magic, version, state, error, chip/core, clocks, CPU state, counters, fault evidence
        return struct.pack("<20I", 0x4E445631, version, state, error, 0x411FC271, 0x20036450,
                           5, 0, 0, 0, 0, ticks, loops, 512, 0, 0, 0, 0, 0, power)

    def test_v2_requires_confirmed_hold_and_button_configuration(self):
        before = self.report.decode(self.dump(version=2, power=15))
        after = self.report.decode(self.dump(20, 200, version=2, power=31))
        self.assertEqual(after['power_status'], 31)
        self.assertTrue(self.report.is_live(after, before))
        for missing in (1, 2, 4, 8):
            bad = self.report.decode(self.dump(20, 200, version=2, power=15 ^ missing))
            self.assertFalse(self.report.is_live(bad, before))
            bad_before = self.report.decode(self.dump(version=2, power=15 ^ missing))
            self.assertFalse(self.report.is_live(after, bad_before))
        self.assertFalse(self.report.is_live(after, self.report.decode(self.dump())))

    def test_valid_dump_is_only_a_snapshot(self):
        result = self.report.decode(self.dump())
        self.assertEqual(result["ticks"], 10)
        self.assertFalse(self.report.is_live(result, None))

    def test_v3_requires_hse_ready_and_selected_in_both_snapshots(self):
        before = self.report.decode(self.dump(version=3, power=15))
        after = self.report.decode(self.dump(20, 200, version=3, power=15))
        for r in (before, after):
            r.update(rcc_cr=0x34025, rcc_cfgr=0x12)
        self.assertTrue(self.report.is_live(after, before))
        for field, value in [('rcc_cr', 0x14025), ('rcc_cfgr', 2),
                             ('rcc_cfgr', 0x10), ('rcc_d1cfgr', 8), ('power_status', 7)]:
            self.assertFalse(self.report.is_live(dict(after, **{field: value}), before))
            self.assertFalse(self.report.is_live(after, dict(before, **{field: value})))

    def test_both_interrupt_and_main_must_advance(self):
        before = self.report.decode(self.dump())
        self.assertTrue(self.report.is_live(self.report.decode(self.dump(20, 200)), before))
        self.assertFalse(self.report.is_live(self.report.decode(self.dump(10, 200)), before))
        self.assertFalse(self.report.is_live(self.report.decode(self.dump(20, 100)), before))
        self.assertFalse(self.report.is_live(self.report.decode(self.dump(0, 0)), before))

    def test_wraparound_and_error_states(self):
        before = self.report.decode(self.dump(0xFFFFFFFE, 0xFFFFFFFE))
        self.assertTrue(self.report.is_live(self.report.decode(self.dump(1, 1)), before))
        for state, error in [(1, 0), (4, 1), (5, 0), (3, 4)]:
            self.assertFalse(self.report.is_live(self.report.decode(self.dump(20, 200, state, error)),
                                                 self.report.decode(self.dump())))

    def test_rejects_wrong_length_magic_and_version(self):
        for data in [b"", self.dump()[:-1], self.dump() + b"\x00", b"oops" + self.dump()[4:],
                     self.dump()[:4] + struct.pack("<I", 4) + self.dump()[8:]]:
            with self.assertRaises(ValueError):
                self.report.decode(data)


if __name__ == "__main__":
    unittest.main()
