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

    def dump(self, ticks=10, loops=100, state=3, error=0):
        # magic, version, state, error, chip/core, clocks, CPU state, counters, fault evidence
        return struct.pack("<20I", 0x4E445631, 1, state, error, 0x411FC271, 0x20036450,
                           5, 0, 0, 0, 0, ticks, loops, 512, 0, 0, 0, 0, 0, 0)

    def test_valid_dump_is_only_a_snapshot(self):
        result = self.report.decode(self.dump())
        self.assertEqual(result["ticks"], 10)
        self.assertFalse(self.report.is_live(result, None))

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
                     self.dump()[:4] + struct.pack("<I", 2) + self.dump()[8:]]:
            with self.assertRaises(ValueError):
                self.report.decode(data)


if __name__ == "__main__":
    unittest.main()
