import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flash_transaction import Transaction
from flash_journal import Journal
from flash_journal import execute
from unittest.mock import Mock

class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'journal.json'
        self.plan=Transaction(b'B'*64,b'A'*512,b'I'*131072,b'X'*1048576)
    def test_exact_seal_required_and_existing_journal_never_overwritten(self):
        with self.assertRaises(ValueError):Journal.create(self.path,self.plan,'install',None)
        self.assertFalse(self.path.exists())
        Journal.create(self.path,self.plan,'install',self.plan.seal)
        with self.assertRaises(FileExistsError):Journal.create(self.path,self.plan,'install',self.plan.seal)
    def test_intent_persisted_dirty_before_command_completion(self):
        j=Journal.create(self.path,self.plan,'install',self.plan.seal)
        j.before('external-erase',0,4096)
        r=Journal.read(self.path)
        self.assertEqual(r['state'],'intent');self.assertTrue(r['external_dirty'])
        self.assertFalse(r['internal_dirty']);self.assertTrue(r['original_resume_forbidden'])
        j.command_complete()
        j.checkpoint('external')
        j.before('internal-erase',0x08000000,131072)
        j.failed('USB disconnected')
        r=Journal.read(self.path)
        self.assertTrue(r['internal_dirty']);self.assertEqual(r['state'],'failed')
    def test_wrong_data_outside_ranges_and_internal_before_external_rejected(self):
        j=Journal.create(self.path,self.plan,'install',self.plan.seal)
        for op,a,data in [('external-erase',1048576,4096),('external-program',0,b'Z'*256),
                           ('internal-program',0x08000000,b'B'*32),('internal-erase',0x08000000,131072)]:
            with self.assertRaises(ValueError):j.before(op,a,data)
        self.assertEqual(Journal.read(self.path)['sequence'],0)
    def test_recovery_starts_dirty_and_can_only_finish_after_verification(self):
        j=Journal.create(self.path,self.plan,'recover',self.plan.recovery_seal)
        self.assertTrue(Journal.read(self.path)['internal_dirty'])
        with self.assertRaises(ValueError):j.finish([])
        j.before('external-erase',0,4096);j.command_complete();j.checkpoint('external')
        j.before('internal-erase',0x08000000,131072);j.command_complete();j.checkpoint('internal')
        j.finish(['original-external-verified','original-internal-verified'])
        self.assertFalse(Journal.read(self.path)['original_resume_forbidden'])
    def test_complete_install_still_prohibits_original_resume(self):
        j=Journal.create(self.path,self.plan,'install',self.plan.seal)
        j.before('external-erase',0,4096);j.command_complete();j.checkpoint('external')
        j.before('internal-erase',0x08000000,131072);j.command_complete();j.checkpoint('internal')
        j.finish(['external-verified','internal-verified'])
        self.assertTrue(Journal.read(self.path)['original_resume_forbidden'])
    def test_verified_stages_cannot_be_mutated_again_or_failed_run_finished(self):
        j=Journal.create(self.path,self.plan,'install',self.plan.seal)
        j.before('external-erase',0,4096);j.command_complete();j.checkpoint('external')
        with self.assertRaises(ValueError):j.before('external-program',0,b'A'*256)
        j.before('internal-erase',0x08000000,131072);j.command_complete();j.checkpoint('internal')
        with self.assertRaises(ValueError):j.before('internal-program',0x08000000,b'B'*32)
        j.failed('failure after verification')
        with self.assertRaises(ValueError):j.finish(['external-verified','internal-verified'])
    def test_coordinator_never_opens_backend_on_bad_authorization(self):
        factory=Mock()
        with self.assertRaises(ValueError):execute(self.plan,factory,'install',None,self.path)
        factory.assert_not_called();self.assertFalse(self.path.exists())
    def test_coordinator_records_interrupt_and_preserves_recovery_dirty_flags(self):
        def interrupted(_):raise KeyboardInterrupt('USB unavailable')
        with self.assertRaises(KeyboardInterrupt):execute(self.plan,interrupted,'recover',self.plan.recovery_seal,self.path)
        r=Journal.read(self.path)
        self.assertEqual(r['state'],'failed')
        self.assertTrue(r['external_dirty']);self.assertTrue(r['internal_dirty'])
        self.assertTrue(r['original_resume_forbidden'])

if __name__=='__main__':unittest.main()
