import struct,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from boot_elf import parse

def fixture():
    off=52+4*32;data=bytearray(off+712)
    struct.pack_into('<16sHHIIIIIHHHHHH',data,0,b'\x7fELF\x01\x01\x01',2,40,1,0x080002c1,52,0,0,52,32,4,0,0,0)
    struct.pack_into('<8I',data,52,1,off,0x08000000,0x08000000,712,712,5,8)
    for at,address,size in [(84,0x24000000,16),(116,0x2400e000,128),(148,0x2400f000,4096)]:
        struct.pack_into('<8I',data,at,1,0,address,address,0,size,6,8)
    struct.pack_into('<176I',data,off,0x24010000,*([0x080002c1]*175))
    return data

class BootFirmwareTests(unittest.TestCase):
    def test_flash_layout_and_rejection_of_bad_vectors_and_physical_storage(self):
        self.assertEqual(parse(fixture())['entry'],'0x80002c1')
        for at,value in [(52+12,0x90000000),(52+20,0x20001),(52+24,7),
                         (116+8,0x24010000),(52+4*32+8,0x24010001)]:
            bad=fixture();struct.pack_into('<I',bad,at,value)
            with self.assertRaises(ValueError):parse(bad)

    def test_real_flash_build_and_stackless_supply_before_ram_initialization(self):
        r=subprocess.run([sys.executable,str(ROOT/'utils/build-tx15-boot.py')],cwd=ROOT,
                         capture_output=True,text=True,encoding='utf8',errors='replace')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        out=ROOT/'local/tx15-hardware/boot';layout=parse((out/'tx15-boot.elf').read_bytes())
        binary=(out/'tx15-boot.bin').read_bytes()
        self.assertEqual(struct.unpack_from('<2I',binary),(0x24010000,int(layout['entry'],16)))
        self.assertLessEqual(len(binary),128*1024)
        tool=ROOT.parent/'tools/arm8/bin/arm-none-eabi-objdump.exe'
        text=subprocess.check_output([str(tool),'-d',str(out/'tx15-boot.elf')],text=True,encoding='utf8',errors='replace')
        startup=text.split('<Boot_Reset>:',1)[1].split('\n\n',1)[0]
        self.assertLess(startup.index('tx15_boot_supply_early'),startup.index('strd'))
        jump=text.split('<tx15_boot_jump>:',1)[1].split('\n\n',1)[0]
        self.assertNotRegex(jump,r'\b(push|pop|bl|blx|sp)\b')
        self.assertIn('msr',jump);self.assertIn('bx',jump)
        copy=text.split('<copy>:',1)[1].split('\n\n',1)[0]
        self.assertRegex(copy,r'\bstrd\s+(?:r\d+|ip|lr),\s*(?:r\d+|ip|lr),\s*\[(?:r\d+|ip|lr)\]',
                         'First AXI ECC initialization must use doubleword destination stores, not stack-only STRD')

if __name__=='__main__':unittest.main()
