import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import flash_geometry as g

def fixture():
    data=bytearray(b'\xff'*1024)
    data[:8]=b'SFDP\x06\x01\x00\xff'
    data[8:16]=bytes([0,6,1,16,0x40,0,0,0xff])
    words=[0]*16
    words[1]=0x07ffffff
    words[7]=0x520f200c  # 4 KiB / 0x20 and 32 KiB / 0x52
    words[8]=0xd810
    words[10]=8<<4
    struct.pack_into('<16I',data,0x40,*words)
    return bytes(data)

class GeometryTests(unittest.TestCase):
    def test_sfdp_capacity_page_and_erase_types(self):
        r=g.parse_sfdp(fixture())
        self.assertEqual(r['capacity_bytes'],16777216)
        self.assertEqual(r['page_bytes'],256)
        self.assertEqual(r['erase_types'],[(4096,0x20),(32768,0x52),(65536,0xd8)])
        self.assertEqual(r['address_bytes'],3)
        data=bytearray(fixture());struct.pack_into('<I',data,0x44,0x8000001b)
        self.assertEqual(g.parse_sfdp(data)['capacity_bytes'],16777216)

    def test_bad_signature_truncation_overlap_and_huge_density_refused(self):
        for data in [b'',fixture()[:15],b'BAD!'+fixture()[4:],fixture()[:100]]:
            with self.assertRaises(ValueError):g.parse_sfdp(data)
        for offset,value in [(12,8),(0x44,0x800000ff),(0x40,2<<17),(0x68,0)]:
            data=bytearray(fixture());struct.pack_into('<I',data,offset,value)
            with self.assertRaises(ValueError):g.parse_sfdp(data)

    def test_nonuniform_map_is_not_silently_treated_as_uniform(self):
        data=bytearray(fixture());data[6]=1
        data[16:24]=bytes([0x81,0,1,1,0x90,0,0,0xff])
        with self.assertRaises(ValueError):g.parse_sfdp(data)

    def test_status_is_observation_not_write_authorization(self):
        info=g.assess(0xc84018,b'\0\x02\x60',fixture())
        self.assertTrue(info['conservative_status_clear'])
        self.assertFalse(info['flash_write_authorized'])
        self.assertIsNone(info['exact_part_suffix'])
        for status in [b'\x01\x02\x60',b'\x04\x02\x60',b'\0\x42\x60',b'\0\x02\x64']:
            self.assertFalse(g.assess(0xc84018,status,fixture())['conservative_status_clear'])
        for jedec in [0xef4018,0xc84017]:
            with self.assertRaises(ValueError):g.assess(jedec,b'\0\0\0',fixture())

if __name__=='__main__':unittest.main()
