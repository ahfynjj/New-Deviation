"""Build real resident image, IRQ ownership, bounds and isolated outputs."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'utils'))
from hardware.boot_elf import parse,binary

class USBBootBuildTests(unittest.TestCase):
    def test_resident_build_and_vectors(self):
        old={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in
             (ROOT/'local/tx15-hardware/boot/tx15-boot.bin',
              ROOT/'local/tx15-hardware/boot-chain/boot-chain.bin') if p.exists()}
        with tempfile.TemporaryDirectory(prefix='USB boot 中文 ') as tmp:
            r=subprocess.run([sys.executable,str(ROOT/'utils/build-tx15-boot.py'),
                '--usb-update','--out',tmp],cwd=ROOT,capture_output=True,text=True,
                encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            folder=Path(tmp);elf=(folder/'tx15-boot-usb.elf').read_bytes()
            raw=(folder/'tx15-boot-usb.bin').read_bytes();layout=parse(elf)
            self.assertEqual(raw,binary(elf));self.assertLessEqual(layout['flash_bytes'],128*1024)
            meta=json.loads((folder/'build.json').read_text())
            self.assertEqual(meta['mode'],'resident-usb-update-candidate')
            self.assertEqual(meta['bin_sha256'],hashlib.sha256(raw).hexdigest())
            nm=ROOT.parent/'tools/arm8/bin/arm-none-eabi-nm.exe'
            text=subprocess.check_output([str(nm),str(folder/'tx15-boot-usb.elf')],text=True)
            symbols={line.split()[2]:int(line.split()[0],16) for line in text.splitlines() if len(line.split())==3}
            vectors=struct.unpack('<176I',raw[:704])
            self.assertEqual(vectors[15],symbols['SysTick_Handler']|1)
            self.assertEqual(vectors[117],symbols['OTG_FS_IRQHandler']|1)
            self.assertEqual(vectors[16],symbols['Boot_Fault']|1)
            for name in ('tx15_boot_supply_early','tx15_boot_jump','tx15_boot_update_run',
                         'tx15_update_nor_erase4k','tx15_update_nor_program','tx15_boot_load'):
                self.assertIn(name,symbols)
            self.assertLessEqual(symbols['_bss_end'],0x2400e000)
            self.assertEqual(symbols['_mailbox_end']-symbols['_mailbox_start'],128)
        for p,digest in old.items():self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),digest)

    def test_cannot_overwrite_legacy_outputs(self):
        for args in (['--usb-update','--ram-chain'],
                     ['--usb-update','--out',str(ROOT/'local/tx15-hardware/boot')]):
            r=subprocess.run([sys.executable,str(ROOT/'utils/build-tx15-boot.py'),*args],cwd=ROOT,
                capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertNotEqual(r.returncode,0)
