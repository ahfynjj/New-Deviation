import hashlib
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import flash_transaction as t

class MemoryBackend:
    def __init__(self):
        self.external=bytearray(b'X'*1048576);self.internal=bytearray(b'I'*131072)
        self.events=[];self.corrupt=False;self.fail_internal=False
    def check_device(self):self.events.append('preflight')
    def read_external(self,a,n):
        data=bytes(self.external[a:a+n])
        return b'!'+data[1:] if self.corrupt and self.events.count('external-program') else data
    def read_internal(self,a,n):return bytes(self.internal[a-0x08000000:a-0x08000000+n])
    def erase_external(self,a,n):
        assert n==4096 and a%4096==0 and 0<=a<=1048576-n
        self.events.append('external-erase');self.external[a:a+n]=b'\xff'*n
    def program_external(self,a,data):
        assert a%256==0 and len(data)==256 and a+len(data)<=1048576
        self.events.append('external-program');self.external[a:a+len(data)]=data
    def erase_internal(self,a,n):
        assert (a,n)==(0x08000000,131072)
        self.events.append('internal-erase')
        if self.fail_internal:raise TimeoutError('Interrupted internal erase')
        self.internal[:]=b'\xff'*n
    def program_internal(self,a,data):
        assert a%32==0 and len(data)==32 and 0x08000000<=a<=0x08020000-32
        self.events.append('internal-program');offset=a-0x08000000;self.internal[offset:offset+32]=data

class TransactionTests(unittest.TestCase):
    def plan(self,b):return t.Transaction(b'B'*64,b'A'*512,bytes(b.internal),bytes(b.external))
    def test_no_matching_authorization_no_device_access(self):
        b=MemoryBackend();p=self.plan(b)
        for token in [None,True,'0'*64]:
            with self.assertRaises(ValueError):t.install(p,b,token)
        self.assertFalse(b.events)

    def test_external_verification_precedes_internal_commit_and_ranges_are_bounded(self):
        b=MemoryBackend();p=self.plan(b);r=t.install(p,b,p.seal)
        self.assertLess(b.events.index('external-program'),b.events.index('internal-erase'))
        self.assertEqual(bytes(b.external[:512]),p.payload)
        self.assertEqual(bytes(b.external[4096:]),p.original_external[4096:])
        self.assertEqual(bytes(b.internal[:64]),p.boot)
        self.assertEqual(bytes(b.internal[64:]),b'\xff'*(131072-64))
        self.assertEqual(r,['external-verified','internal-verified'])

    def test_mismatched_live_original_aborts_before_any_erase(self):
        b=MemoryBackend();p=self.plan(b);b.external[999999]=0
        with self.assertRaises(ValueError):t.install(p,b,p.seal)
        self.assertEqual(b.events,['preflight'])

    def test_native_app_update_keeps_identical_internal_loader(self):
        b=MemoryBackend();b.internal[:]=b'B'*64+b'\xff'*(131072-64)
        p=self.plan(b)
        self.assertEqual(t.install(p,b,p.seal),['external-verified','internal-verified'])
        self.assertNotIn('internal-erase',b.events)
        self.assertNotIn('internal-program',b.events)
        self.assertEqual(bytes(b.internal),p.original_internal)

    def test_unchanged_loader_is_rechecked_after_external_update(self):
        class DamagedLoader(MemoryBackend):
            def program_external(self,a,data):
                super().program_external(a,data);self.internal[90000]=0
        b=DamagedLoader();b.internal[:]=b'B'*64+b'\xff'*(131072-64);p=self.plan(b)
        with self.assertRaises(t.WriteFailure):t.install(p,b,p.seal)
        self.assertNotIn('internal-erase',b.events)

    def test_external_readback_failure_never_replaces_internal_boot(self):
        b=MemoryBackend();p=self.plan(b);b.corrupt=True
        with self.assertRaises(t.WriteFailure) as error:t.install(p,b,p.seal)
        self.assertTrue(error.exception.external_dirty)
        self.assertFalse(error.exception.internal_dirty)
        self.assertNotIn('internal-erase',b.events)
        self.assertEqual(bytes(b.internal),p.original_internal)

    def test_interruption_marks_internal_dirty_before_starting_erase(self):
        b=MemoryBackend();p=self.plan(b);b.fail_internal=True
        with self.assertRaises(t.WriteFailure) as error:t.install(p,b,p.seal)
        self.assertTrue(error.exception.internal_dirty)

    def test_recovery_verifies_external_before_restoring_internal(self):
        b=MemoryBackend();p=self.plan(b)
        b.external[:]=b'\0'*1048576;b.internal[:]=b'\0'*131072
        t.recover(p,b,p.recovery_seal)
        self.assertEqual(bytes(b.external),p.original_external)
        self.assertEqual(bytes(b.internal),p.original_internal)
        self.assertLess(b.events.index('external-program'),b.events.index('internal-erase'))

    def test_unaligned_or_oversized_transaction_refused(self):
        b=MemoryBackend()
        for boot,payload in [(b'B',b'A'*256),(b'B'*32,b'A'),(b'B'*131104,b'A'*256),(b'B'*32,b'A'*1048832)]:
            with self.assertRaises(ValueError):t.Transaction(boot,payload,bytes(b.internal),bytes(b.external))

    def test_ctrl_c_after_erase_keeps_dirty_state_available(self):
        from unittest.mock import patch
        for method,internal_dirty in [('erase_external',False),('erase_internal',True)]:
            b=MemoryBackend();p=self.plan(b)
            with patch.object(b,method,side_effect=KeyboardInterrupt):
                with self.assertRaises(t.WriteFailure) as error:t.install(p,b,p.seal)
            self.assertTrue(error.exception.external_dirty)
            self.assertEqual(error.exception.internal_dirty,internal_dirty)

    def test_failed_recovery_cannot_claim_existing_internal_image_is_clean(self):
        b=MemoryBackend();p=self.plan(b);b.internal[:]=b'\0'*131072;b.corrupt=True
        with self.assertRaises(t.WriteFailure) as error:t.recover(p,b,p.recovery_seal)
        self.assertTrue(error.exception.internal_dirty)
        self.assertNotIn('internal-erase',b.events)

    def test_failed_or_unrestored_observation_cannot_prepare_installation(self):
        from test_flash_geometry import fixture
        import struct
        r={'status':'ram_live_verified','cleanup_errors':[], 'ram_run':{
            'context_restored':True,'live':True,'recovery_errors':[],
            'qspi':{'jedec_id':'0xc84018','backup_prefix_matches':True},
            'flash_info_raw_hex':(struct.pack('<II',0x46494e31,0)+b'\0\x02\x20\0'+fixture()).hex()}}
        self.assertTrue(t.validated_observation(r)['conservative_status_clear'])
        r['ram_run']['context_restored']=False
        with self.assertRaises(ValueError):t.validated_observation(r)

    def test_frozen_first_bundle_geometry_and_backups(self):
        root=Path(__file__).resolve().parents[3]
        from install_kit import read
        p=read(root/'local/tx15-hardware/install/kit').plan
        self.assertEqual(len(p.boot),6880)
        self.assertEqual(len(p.payload)%256,0)
        self.assertGreaterEqual(p.erase_bytes,len(p.payload))
        self.assertEqual(p.erase_bytes%4096,0)
        self.assertLessEqual(p.erase_bytes,1048576)
        self.assertFalse(p.manifest()['flash_write_authorized'])
