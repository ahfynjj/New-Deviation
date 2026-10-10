"""No reset/upload without explicit arm, exact candidate and held-power proof."""
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'utils/hardware'))


class USBProbeSessionTests(unittest.TestCase):
    def module(self):
        try: return importlib.import_module('usb_probe_session')
        except ModuleNotFoundError: self.fail('USB probe upload gate is missing')

    def test_default_is_offline_and_bad_candidate_never_opens_probe(self):
        api=self.module();opener=Mock(side_effect=AssertionError('Unexpected probe opening'))
        with tempfile.TemporaryDirectory() as tmp:
            # Missing/unknown candidate is rejected before any hardware lease.
            with self.assertRaises((ValueError,OSError)):
                api.run(Path(tmp),armed=True,expected_sha='0'*64,opener=opener,held=lambda:None)
            opener.assert_not_called()

    def test_valid_offline_candidate_and_exact_approval_gates(self):
        api=self.module();folder=ROOT/'local/tx15-hardware/usb-probe'
        # Build the actual candidate in isolation; fixture never relaxes a hash.
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            r=subprocess.run([sys.executable,str(ROOT/'utils/build-tx15-usb.py'),'--probe','--out',tmp],
                capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stderr)
            folder=Path(tmp);meta=json.loads((folder/'build.json').read_text())
            opener=Mock(side_effect=AssertionError('Unexpected probe opening'))
            report=api.run(folder,armed=False,opener=opener)
            self.assertTrue(report['offline']);self.assertEqual(report['flash_mutation_commands'],0)
            for expected,held in ((None,lambda:None),('0'*64,lambda:None),(meta['bin_sha256'],None)):
                with self.assertRaises(ValueError):
                    api.run(folder,armed=True,expected_sha=expected,held=held,opener=opener)
            opener.assert_not_called()
            raw=bytearray((folder/'tx15-usb-probe.bin').read_bytes());raw[-1]^=1
            (folder/'tx15-usb-probe.bin').write_bytes(raw)
            with self.assertRaises(ValueError):api.run(folder,armed=True,expected_sha=meta['bin_sha256'],held=lambda:None,opener=opener)
            opener.assert_not_called()

    def test_upload_requires_verified_halt_and_never_uses_flash_backend(self):
        api=self.module()
        # Missing environment proof rejects upload, and the caller's finally
        # handles halt/close. No CPU register or RAM mutation is allowed here.
        context=Mock();context.report={};context.io.read32.return_value=0x30003
        with self.assertRaises(RuntimeError):api.launch(context,b'\0'*704,0x240002c1)
        context._write.assert_not_called();context.backend.assert_not_called()
