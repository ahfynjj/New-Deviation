"""New approval domain and frozen installed app; no hardware accessed."""
import importlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'utils/hardware'))
from unittest.mock import Mock
import status_update,native_update,install_entry,install_kit
from utils.hardware.tests.build_fixtures import candidate_root,ROOT

class USBBootKitTests(unittest.TestCase):
    def setUp(self):
        try:self.api=importlib.import_module('usb_boot_update')
        except ModuleNotFoundError:self.fail('USB boot installation kit missing')
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=candidate_root(self.tmp.name,True)
        shutil.copytree(ROOT/'local/tx15-hardware/boot-usb',self.root/'local/tx15-hardware/boot-usb')
        self.baseline=ROOT/'local/tx15-hardware/install/calibration-kit'
        self.base,_=status_update.baseline(ROOT,self.baseline)
        self.internal,self.external=native_update.baseline_images(self.base)
        self.external=self.external[:0xf0000]+bytes(range(256))*256
        self.folder=Path(self.tmp.name)/'USB kit'
    def prepare(self):return self.api.prepare(self.root,self.folder,self.baseline,self.internal,self.external)
    def test_preserve_live_app_and_require_new_approval(self):
        kit=self.prepare();self.assertEqual(kit.plan.original_external,self.external)
        self.assertEqual(kit.plan.payload,self.base.plan.payload)
        self.assertNotEqual(kit.plan.boot,self.base.plan.boot)
        self.assertLessEqual(kit.plan.erase_bytes,0xf0000)
        opener=Mock()
        with self.assertRaises(ValueError):install_entry.authorized_run(kit,'install',self.base.approval('install'),opener)
        opener.assert_not_called();self.assertNotEqual(kit.approval('install'),kit.approval('recover'))
        archive=self.api.export_recovery(kit,Path(self.tmp.name)/'recovery.zip')
        self.assertTrue(archive.exists());self.assertEqual(self.api.read(self.folder).plan,kit.plan)
        checklist=self.api.checklist(kit)
        self.assertEqual(checklist['internal_erase_bytes'],131072)
        self.assertTrue(checklist['application_unchanged'])
        self.assertFalse(checklist['flash_write_authorized'])
        with self.assertRaises(ValueError):install_kit.read(self.folder)
    def test_unknown_baseline_rejected_before_creating_folder(self):
        for internal,external in ((b'!'+self.internal[1:],self.external),
                                  (self.internal,b'!'+self.external[1:])):
            with self.assertRaises(ValueError):self.api.prepare(self.root,self.folder,self.baseline,internal,external)
            self.assertFalse(self.folder.exists())
    def test_reuse_verified_snapshot_is_offline_and_keeps_existing_settings(self):
        source=ROOT/'local/tx15-hardware/install/elrs-commands-kit'
        snapshot=status_update.read_native(source)
        kit=self.api.reuse_snapshot(self.root,self.folder,self.baseline,source)
        self.assertEqual(kit.plan.original_internal,snapshot.plan.original_internal)
        self.assertEqual(kit.plan.original_external,snapshot.plan.original_external)
        self.assertEqual(kit.plan.payload,self.base.plan.payload)
        bad=Path(self.tmp.name)/'bad snapshot'
        shutil.copytree(source,bad)
        path=bad/'original-external.bin';data=path.read_bytes();path.write_bytes(b'!'+data[1:])
        with self.assertRaises(ValueError):
            self.api.reuse_snapshot(self.root,Path(self.tmp.name)/'rejected kit',self.baseline,bad)
        self.assertFalse((Path(self.tmp.name)/'rejected kit').exists())
    def test_tampered_app_boot_or_uid_rejected_even_if_rehashed(self):
        kit=self.prepare()
        original=(self.folder/'kit.json').read_bytes()
        for name in ('boot.bin','payload.bin','original-external.bin'):
            path=self.folder/name;data=path.read_bytes();bad=b'!'+data[1:];path.write_bytes(bad)
            manifest=json.loads(original);manifest['files'][name]=self.api.sha(bad)
            (self.folder/'kit.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):self.api.read(self.folder)
            path.write_bytes(data);(self.folder/'kit.json').write_bytes(original)
        manifest=json.loads(original);manifest['device_uid']='ab'*12
        (self.folder/'kit.json').write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):self.api.read(self.folder)
