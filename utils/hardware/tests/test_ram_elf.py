import importlib.util
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[3]


class RamElfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "utils/hardware/check_ram_elf.py"
        spec = importlib.util.spec_from_file_location("ram_elf", path)
        cls.reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.reader)
        cls.elf = (ROOT / "local/tx15-hardware/ram-probe/ram-probe.elf").read_bytes()

    def test_actual_cross_compiled_image(self):
        result = self.reader.check(self.elf)
        self.assertEqual(result["stack_top"], "0x24010000")

    def test_rejects_flash_load_even_if_vectors_look_valid(self):
        data = bytearray(self.elf)
        phoff = struct.unpack_from("<I", data, 28)[0]
        struct.pack_into("<II", data, phoff + 8, 0x08000000, 0x08000000)
        with self.assertRaises(ValueError):
            self.reader.check(data)

    def test_rejects_missing_or_moved_reservations(self):
        phoff = struct.unpack_from("<I", self.elf, 28)[0]
        for index in (1, 2):
            data = bytearray(self.elf)
            struct.pack_into("<I", data, phoff + index * 32, 0)  # hide PT_LOAD
            with self.assertRaises(ValueError):
                self.reader.check(data)
            data = bytearray(self.elf)
            address = 0x2400D000 if index == 1 else 0x2400E800
            struct.pack_into("<II", data, phoff + index * 32 + 8, address, address)
            with self.assertRaises(ValueError):
                self.reader.check(data)

    def test_rejects_bad_entry_stack_and_truncated_elf(self):
        data = bytearray(self.elf)
        struct.pack_into("<I", data, 24, 0x24000000)
        with self.assertRaises(ValueError):
            self.reader.check(data)
        data = bytearray(self.elf)
        phoff = struct.unpack_from("<I", data, 28)[0]
        vector_offset = struct.unpack_from("<I", data, phoff + 4)[0]
        struct.pack_into("<I", data, vector_offset, 0x20020000)
        with self.assertRaises(ValueError):
            self.reader.check(data)
        with self.assertRaises(ValueError):
            self.reader.check(self.elf[:100])
