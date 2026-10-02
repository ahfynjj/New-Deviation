import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from crsf_parameters import decode

class ParameterDecodeTests(unittest.TestCase):
    def test_select_and_hidden(self):
        d=decode(bytes([0,0x89])+b'Rate\0Off;;Fast\0'+bytes([2,0,2,0])+b'Hz\0')
        self.assertEqual((d['name'],d['value'],d['index'],d['hidden']),('Rate','Fast',2,True))
        self.assertEqual(d['options'],['Off','','Fast'])
    def test_signed_and_float(self):
        d=decode(bytes([0,3])+b'Gain\0'+(-150).to_bytes(2,'big',signed=True)*4+b'dB\0')
        self.assertEqual(d['value'],-150)
        d=decode(bytes([0,8])+b'Fine\0'+(-125).to_bytes(4,'big',signed=True)*4+bytes([2])+(5).to_bytes(4,'big')+b'V\0')
        self.assertEqual((d['value'],d['raw_value'],d['unit']),(-1.25,-125,'V'))
    def test_info_command_and_folder(self):
        self.assertEqual(decode(b'\0\14Version\0v4\0')['value'],'v4')
        self.assertEqual(decode(b'\0\15Bind\0\0\12Ready\0')['status'],0)
        self.assertEqual(decode(b'\0\13Power\0')['type'],'folder')
    def test_invalid_never_reads_past_end(self):
        for data in (b'',b'\0\11missing',b'\0\11X\0A;B\0\1',b'\0\10F\0\0'):
            self.assertIn('error',decode(data))
