import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from boot_only_update import Plan, BootJournal, execute
from flash_journal import Journal


class Backend:
    def __init__(self, internal, external):
        self.internal = internal
        self.external = external
        self.mutations = []
    def check_device(self): pass
    def read_internal(self, address, size):
        return self.internal[address-0x08000000:address-0x08000000+size]
    def read_external(self, offset, size): return self.external[offset:offset+size]
    def erase_internal(self, address, size):
        self.journal.before('internal-erase', address, size)
        self.mutations.append('erase')
        self.internal = b'\xff'*131072
        self.journal.command_complete()
    def program_internal(self, address, data):
        self.journal.before('internal-program', address, data)
        self.mutations.append('program')
        offset = address-0x08000000
        self.internal = self.internal[:offset]+data+self.internal[offset+len(data):]
        self.journal.command_complete()


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'journal.json'
        self.plan = Plan(b'B'*64, b'I'*131072, b'X'*1048576)
        self.backend = Backend(self.plan.original_internal, self.plan.original_external)
    def run_update(self, action='install', seal=None):
        def factory(j): self.backend.journal = j; return self.backend
        return execute(self.plan, factory, action, seal or self.plan.seal, self.path)
    def test_install_only_internal_and_verify_external(self):
        self.run_update()
        self.assertEqual(self.backend.internal, b'B'*64+b'\xff'*(131072-64))
        self.assertEqual(self.backend.external, self.plan.original_external)
        record = Journal.read(self.path)
        self.assertFalse(record['external_dirty'])
        self.assertEqual(record['state'], 'installed')
    def test_wrong_seal_never_opens_backend(self):
        with self.assertRaises(ValueError): self.run_update(seal='wrong')
        self.assertFalse(self.path.exists())
        self.assertEqual(self.backend.mutations, [])
    def test_changed_original_blocks_erase(self):
        self.backend.internal = b'Z'*131072
        with self.assertRaises(ValueError): self.run_update()
        self.assertEqual(self.backend.mutations, [])
    def test_external_intents_always_refused(self):
        j = BootJournal.create(self.path, self.plan, 'install', self.plan.seal)
        for op, data in [('external-erase',4096), ('external-program',b'X'*256)]:
            with self.assertRaises(ValueError): j.before(op, 0, data)
        self.assertFalse(Journal.read(self.path)['external_dirty'])
    def test_corrupt_external_after_internal_write_is_failure(self):
        original = self.backend.program_internal
        def change(address, data):
            original(address, data)
            self.backend.external = b'Z'*1048576
        self.backend.program_internal = change
        with self.assertRaises(RuntimeError): self.run_update()
        self.assertEqual(Journal.read(self.path)['state'], 'failed')
    def test_interrupted_write_records_dirty_and_recover_only_internal(self):
        original = self.backend.program_internal
        def stop(address, data):
            self.backend.journal.before('internal-program', address, data)
            raise KeyboardInterrupt()
        self.backend.program_internal = stop
        with self.assertRaises(KeyboardInterrupt): self.run_update()
        self.assertTrue(Journal.read(self.path)['internal_dirty'])
        self.assertFalse(Journal.read(self.path)['external_dirty'])
        self.path = self.path.with_name('recover.json')
        self.backend.program_internal = original
        self.run_update('recover', self.plan.recovery_seal)
        self.assertEqual(self.backend.internal, self.plan.original_internal)
        self.assertFalse(Journal.read(self.path)['external_dirty'])

if __name__ == '__main__': unittest.main()
