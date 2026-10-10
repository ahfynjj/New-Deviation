"""Build the actual RAM probe, validate load map and prohibit NOR mutation code."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'utils'))
from hardware.check_ram_elf import check


class USBProbeBuildTests(unittest.TestCase):
    def test_actual_ram_probe_isolated_from_legacy_and_no_nor_writer(self):
        builder=ROOT/'utils/build-tx15-usb.py'
        self.assertTrue(builder.exists(),'USB RAM probe builder is missing')
        legacy=[ROOT/'local/tx15-hardware/boot/tx15-boot.bin',
                ROOT/'local/tx15-hardware/app-standalone/tx15-app.nd15']
        old={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in legacy if p.exists()}
        with tempfile.TemporaryDirectory(prefix='USB build ') as tmp:
            r=subprocess.run([sys.executable,str(builder),'--probe','--out',tmp],cwd=ROOT,
                capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            folder=Path(tmp);elf=(folder/'tx15-usb-probe.elf').read_bytes()
            layout=check(elf)
            meta=json.loads((folder/'build.json').read_text())
            self.assertEqual(meta['mode'],'usb-readonly-ram-probe')
            self.assertFalse(meta['flash_mutation_linked'])
            self.assertEqual(meta['entry'],int(layout['entry'],16))
            self.assertEqual(meta['elf_sha256'],hashlib.sha256(elf).hexdigest())
            nm=ROOT.parent/'tools/arm8/bin/arm-none-eabi-nm.exe'
            symbols=subprocess.check_output([str(nm),str(folder/'tx15-usb-probe.elf')],text=True)
            for forbidden in ('tx15_update_tx_prepare','tx15_update_nor_erase','tx15_update_nor_program'):
                self.assertNotIn(forbidden,symbols)
            self.assertIn('OTG_FS_IRQHandler',symbols)
        for p,digest in old.items(): self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),digest)
