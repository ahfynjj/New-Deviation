import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import install_kit as k
import install_entry as e
from flash_transaction import load_bundle
from flash_transaction import Transaction,sha
from dataclasses import replace

ROOT=Path(__file__).resolve().parents[3]
UID='010000000200000003000000'

class KitTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)/'kit'
    def test_frozen_kit_verifies_without_build_outputs_or_full_external_backup(self):
        prepared=k.prepare(ROOT,self.folder,UID)
        kit=k.read(self.folder)
        self.assertEqual(kit.plan,load_bundle(ROOT))
        self.assertEqual(kit.uid,UID)
        self.assertEqual(prepared,kit.manifest)
        self.assertEqual(len((self.folder/'original-external.bin').read_bytes()),1048576)
        self.assertNotEqual(kit.approval('install'),kit.plan.seal)
    def test_changed_image_or_manifest_is_rejected(self):
        k.prepare(ROOT,self.folder,UID)
        p=self.folder/'boot.bin';data=p.read_bytes();p.write_bytes(b'!'+data[1:])
        with self.assertRaises(ValueError):k.read(self.folder)
    def test_prepare_never_overwrites_existing_kit(self):
        k.prepare(ROOT,self.folder,UID)
        with self.assertRaises(FileExistsError):k.prepare(ROOT,self.folder,UID)
    def test_changed_candidate_rejected_even_with_recomputed_manifest(self):
        k.prepare(ROOT,self.folder,UID)
        kit=k.read(self.folder)
        data=b'!'+kit.plan.boot[1:];(self.folder/'boot.bin').write_bytes(data)
        manifest=kit.manifest;manifest['files']['boot.bin']=sha(data)
        manifest['transaction']=replace(kit.plan,boot=data).manifest()
        (self.folder/'kit.json').write_text(json.dumps(manifest),encoding='utf8')
        with self.assertRaises(ValueError):k.read(self.folder)
    def test_missing_or_bad_uid_rejected_without_creating_kit(self):
        for uid in ('','ff'*12,'00'*12,'not-hex'):
            with self.assertRaises(ValueError):k.prepare(ROOT,self.folder,uid)
        self.assertFalse(self.folder.exists())

class EntryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)/'kit';k.prepare(ROOT,self.folder,UID)
        self.kit=k.read(self.folder)
    def test_no_exact_approval_never_opens_target(self):
        opener=Mock()
        for token in (None,self.kit.plan.seal,self.kit.approval('recover')):
            with self.assertRaises(ValueError):e.authorized_run(self.kit,'install',token,opener)
        opener.assert_not_called()
    def test_dirty_or_corrupt_active_record_blocks_install_before_open(self):
        p=self.folder/'active.json'
        p.write_text('{broken',encoding='utf8')
        opener=Mock()
        with self.assertRaises(ValueError):e.authorized_run(self.kit,'install',self.kit.approval('install'),opener)
        opener.assert_not_called()
    def test_os_lease_prevents_parallel_sessions_and_releases_after_exception(self):
        with e.lease(self.folder):
            with self.assertRaises(OSError):
                with e.lease(self.folder):pass
        with e.lease(self.folder):pass
    def test_bootstrap_or_uid_failure_never_calls_transaction(self):
        context=Mock();context.enter.side_effect=RuntimeError('Wrong MCU UID')
        with self.assertRaises(RuntimeError):
            e.authorized_run(self.kit,'recover',self.kit.approval('recover'),lambda:context)
        context.hold.assert_called_once();context.close.assert_called_once()
        self.assertFalse((self.folder/'active.json').exists())
    def test_install_checkpoint_success_marks_active_and_blocks_second_install(self):
        from test_swd_flash import Registers
        from swd_flash import SWDFlash
        io=Registers()
        kit=replace(self.kit,plan=Transaction(b'B'*64,b'A'*512,bytes(io.internal),bytes(io.ext)))
        context=Mock();context.report={}
        context.backend.side_effect=lambda journal,read_only:SWDFlash(io,journal)
        e.authorized_run(kit,'install',kit.approval('install'),lambda:context)
        record=e.active(kit)
        self.assertEqual(record['state'],'installed');self.assertTrue(record['original_resume_forbidden'])
        context.hold.assert_called_once();context.close.assert_called_once()
        opener=Mock()
        with self.assertRaises(ValueError):e.authorized_run(kit,'install',kit.approval('install'),opener)
        opener.assert_not_called()
    def test_hold_failure_does_not_mask_primary_and_close_is_attempted(self):
        context=Mock();context.report={};context.hold.side_effect=OSError('USB lost')
        context.close.side_effect=OSError('close failed')
        primary=RuntimeError('program interrupted')
        with self.assertRaises(RuntimeError) as caught:
            try:raise primary
            finally:e.finish_context(context)
        self.assertIs(caught.exception,primary)
        context.close.assert_called_once()
        self.assertEqual(len(context.report['exit_errors']),2)
    def test_active_pointer_storage_failure_never_constructs_mutating_backend(self):
        from unittest.mock import patch
        context=Mock();context.report={}
        with patch.object(e,'activate',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):e.authorized_run(self.kit,'install',self.kit.approval('install'),lambda:context)
        context.backend.assert_not_called();context.hold.assert_called_once();context.close.assert_called_once()
        self.assertFalse((self.folder/'active.json').exists())

if __name__=='__main__':unittest.main()
