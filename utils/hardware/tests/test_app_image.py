import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app_image import parse,allowed,transfer_chunks

class AppImageTests(unittest.TestCase):
    def image(self):
        data=bytearray(52+96+704+16)
        struct.pack_into('<16sHHIIIIIHHHHHH',data,0,b'\x7fELF\x01\x01\x01',2,40,1,0x240102c1,52,0,0,52,32,3,0,0,0)
        # Include one Thumb instruction-sized payload after vectors.
        data.extend(bytes(8))
        struct.pack_into('<8I',data,52,1,148,0x24010000,0x24010000,712,720,7,8)
        struct.pack_into('<8I',data,84,1,0,0x2407c000,0x2407c000,0,16384,6,8)
        struct.pack_into('<8I',data,116,1,860,0xd0080000,0xd0080000,16,16,4,8)
        struct.pack_into('<176I',data,148,0x24080000,*([0x240102c1]*175))
        return data
    def test_layout_and_excluded_bootstrap_flash(self):
        parse(self.image())
        for a in (0x08000000,0x90000000,0x24000000,0x2400e000,0x2407c000,0xd0000000):
            self.assertFalse(allowed(a,4))
    def test_reject_mutated_load_address_and_vector(self):
        for va in (0x08000000,0x24000000,0xd0000000):
            data=self.image();struct.pack_into('<II',data,60,va,va)
            with self.assertRaises(ValueError): parse(data)
        data=self.image();struct.pack_into('<I',data,160,0x08000001)
        with self.assertRaises(ValueError): parse(data)
    def test_bulk_chunks_never_cross_ap_wrap_or_owned_region(self):
        chunks=list(transfer_chunks(0xd00803f8,bytes(1051)))
        self.assertEqual(sum(len(b) for a,b in chunks),1056)
        for a,b in chunks:
            self.assertLessEqual(a%1024+len(b),1024)
            self.assertTrue(allowed(a,len(b)))
        with self.assertRaises(ValueError): list(transfer_chunks(0x2407bff8,bytes(9)))

class BenchModelTests(unittest.TestCase):
 def test_every_mixer_destination_has_enabled_template(self):
  from pathlib import Path
  root=Path(__file__).resolve().parents[3]
  sections=[]
  for line in (root/'hardware/tx15/app/model.ini').read_text().splitlines():
   if line.startswith('['): sections.append((line[1:-1].lower(),{}))
   elif '=' in line and sections:
    k,v=line.split('=',1);sections[-1][1][k]=v
  channels={name:values for name,values in sections if name.startswith('channel')}
  mixers=[values for name,values in sections if name=='mixer']
  self.assertEqual(len(mixers),6)
  self.assertEqual([m['src'] for m in mixers],['AIL','ELE','THR','RUD','S1','S2'])
  for m in mixers:
   channel='channel'+m['dest'][2:]
   self.assertEqual(channels.get(channel,{}).get('template'),'simple')

 def test_native_layout_displays_all_six_outputs(self):
  from pathlib import Path
  root=Path(__file__).resolve().parents[3]
  layout=(root/'hardware/tx15/app/layout.ini').read_text()
  self.assertIn('[gui-480x320]',layout)
  bars=[line.split('=',1)[1].split(',') for line in layout.splitlines() if line.startswith('Bargraph=')]
  self.assertEqual([bar[2] for bar in bars],['Ch1','Ch2','Ch3','Ch4','Ch5','Ch6'])
  for x,y,source in bars:
   self.assertTrue(0<=int(x)<=460 and 32<=int(y)<=240)
