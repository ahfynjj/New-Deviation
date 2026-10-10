"""Freeze a native app update without changing first-install/recovery guards."""
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'utils/hardware'))
from utils.hardware.tests.build_fixtures import candidate_root

class NativeUpdateTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=candidate_root(tmp.name,False)
    def module(self):
        self.assertTrue((ROOT/'utils/hardware/native_update.py').exists(), 'Native update kit missing')
        return importlib.import_module('native_update')

    def test_freezes_current_native_baseline_and_preserves_loader(self):
        module=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'kit';module.prepare(self.root,folder)
            kit=module.read(folder)
            self.assertEqual(kit.plan.original_internal,kit.plan.boot+b'\xff'*(131072-len(kit.plan.boot)))
            self.assertEqual(len(kit.plan.original_external),1048576)
            self.assertNotEqual(kit.approval('install'),kit.approval('recover'))
            self.assertFalse(kit.manifest['rf_enabled'])
            self.assertEqual(kit.plan.original_external[:64],(ROOT/'local/tx15-hardware/install/kit/payload.bin').read_bytes()[:64])
            with self.assertRaises(FileExistsError):module.prepare(self.root,folder)

    def test_rejects_rf_metadata_even_with_matching_file_digest(self):
        module=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'kit';module.prepare(self.root,folder)
            metadata=json.loads((folder/'build.json').read_text());metadata['rf_enabled']=True
            (folder/'build.json').write_text(json.dumps(metadata),encoding='utf8')
            manifest=json.loads((folder/'kit.json').read_text())
            manifest['files']['build.json']=module.sha((folder/'build.json').read_bytes())
            (folder/'kit.json').write_text(json.dumps(manifest),encoding='utf8')
            with self.assertRaises(ValueError):module.read(folder)

    def test_rejects_altered_native_baseline_even_with_matching_digest(self):
        module=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'kit';module.prepare(self.root,folder)
            data=bytearray((folder/'original-external.bin').read_bytes());data[999999]^=1
            (folder/'original-external.bin').write_bytes(data)
            manifest=json.loads((folder/'kit.json').read_text())
            manifest['files']['original-external.bin']=module.sha(data)
            (folder/'kit.json').write_text(json.dumps(manifest),encoding='utf8')
            with self.assertRaises(ValueError):module.read(folder)
