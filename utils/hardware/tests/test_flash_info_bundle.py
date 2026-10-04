import json
import struct
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'utils/hardware'))
import flash_info_bundle as b

class FlashInfoBundleTests(unittest.TestCase):
    def test_exact_read_only_bundle_and_initialized_report_addresses(self):
        binary,layout,prefix=b.validate(ROOT)
        self.assertEqual(len(binary),3816)
        self.assertEqual(len(prefix),64)
        self.assertEqual(layout['entry'],'0x240002c1')
        self.assertGreater(b.INFO_ADDR,len(binary)+0x24000000-1)
        self.assertLess(b.QSPI_ADDR+72,0x2400e000)

    def test_report_refuses_failed_incomplete_and_mixed_identity(self):
        from test_flash_geometry import fixture
        data=struct.pack('<II',0x46494e31,0)+b'\0\x02\x60\0'+fixture()
        r=b.decode(data,0xc84018)
        self.assertTrue(r['conservative_status_clear'])
        for invalid in [data[:-1],bytes(len(data)),struct.pack('<II',0x46494e31,2)+data[8:]]:
            with self.assertRaises(ValueError):b.decode(invalid,0xc84018)
        with self.assertRaises(ValueError):b.decode(data,0xef4018)
