"""Host safety: durable backup, same device/session, one COMMIT, verified DONE."""
import importlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from test_usb_update_package import fixture
from usb_update.protocol import Frame,FrameCodec,Opcode,State,encode

UID=bytes.fromhex('1c0039000e51333234363236')

class FakeTransport:
    def __init__(self):
        self.codec=FrameCodec();self.pending=bytearray();self.commands=[]
        self.session=123;self.uid=UID;self.flags=2;self.sfdp=1
        self.total=0;self.crc=0;self.received=0;self.state=State.IDLE
        self.settings=bytes(range(256))*256;self.drop_commit=False;self.disconnect=False
        self.done_flags=1;self.bad_reply=False;self.now=0.;self.done_crc=None
        self.disconnect_commit=False
        self.fail_commit=False
    def write(self,data):
        if self.disconnect:raise OSError('unplugged')
        n=min(17,len(data))
        for f in self.codec.feed(data[:n]):self.respond(f)
        return n
    def read(self,n):
        self.now+=.05
        if self.disconnect:raise OSError('unplugged')
        n=min(n,23,len(self.pending));data=bytes(self.pending[:n]);del self.pending[:n];return data
    def close(self):pass
    def respond(self,f):
        self.commands.append(f)
        if f.kind==Opcode.HELLO:
            payload=self.uid+struct.pack('<8I4B',1,1,0xec040,self.flags,0xc84018,0x1000000,256,4096,0,2,0x60,self.sfdp)
        elif f.kind==Opcode.READ_SETTINGS:
            size=struct.unpack('<I',f.payload)[0];payload=self.settings[f.offset:f.offset+size]
            if self.bad_reply:payload=payload[:-1]
        else:
            if f.kind==Opcode.BEGIN:self.total,self.crc=struct.unpack_from('<2I',f.payload,16);self.state=State.RECEIVING
            if f.kind==Opcode.DATA:self.received+=len(f.payload)
            if f.kind==Opcode.FINALIZE:self.state=State.READY
            if f.kind==Opcode.COMMIT:
                self.state=State.VERIFYING
                if self.fail_commit:self.state=State.ERROR
                if self.disconnect_commit:self.disconnect=True;return
                if self.drop_commit:return
            if f.kind==Opcode.STATUS and self.state==State.VERIFYING:self.state=State.DONE
            crc=self.done_crc if self.done_crc is not None and self.state==State.DONE else self.crc
            payload=struct.pack('<6I',self.state,10 if self.state==State.ERROR else 0,self.received,self.total,crc,self.done_flags if self.state==State.DONE else 0)
        self.pending+=encode(Frame(f.kind|0x80,self.session,f.sequence,f.offset,payload))

class ClientTests(unittest.TestCase):
    def setUp(self):
        try:self.api=importlib.import_module('usb_update.client')
        except ModuleNotFoundError:self.fail('Dedicated updater client missing')
        self.tmp=tempfile.TemporaryDirectory(prefix='更新 备份 ');self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name);self.port=FakeTransport()
        self.client=self.api.UpdaterClient(self.port,self.folder,lambda *args:None,
            clock=lambda:self.port.now,sleep=lambda seconds:setattr(self.port,'now',self.port.now+seconds))
        self.client.connect(expected_uid=UID)
    def commits(self):return [f for f in self.port.commands if f.kind==Opcode.COMMIT]
    def test_success_partial_transport_and_chinese_backup(self):
        prepared=self.client.prepare(fixture())
        self.assertEqual(prepared.backup_path.read_bytes(),self.port.settings)
        self.assertEqual(prepared.uid,UID);self.assertFalse(self.commits())
        result=self.client.commit(prepared)
        self.assertTrue(result.success);self.assertEqual(len(self.commits()),1)
        with self.assertRaises(RuntimeError):self.client.commit(prepared)
        self.assertEqual(len(self.commits()),1)
    def test_backup_disk_failure_fsync_failure_and_bad_read_never_commit(self):
        for method in ('disk','fsync','read'):
            with self.subTest(method=method):
                if method=='read':
                    self.port.bad_reply=True
                    with self.assertRaises(RuntimeError):self.client.prepare(fixture())
                else:
                    target='usb_update.client.save_backup' if method=='disk' else 'usb_update.client.os.fsync'
                    with patch(target,side_effect=OSError('disk full')):
                        with self.assertRaises(OSError):self.client.prepare(fixture())
                self.assertFalse(self.commits())
    def test_cancel_never_commit(self):
        with self.assertRaises(self.api.UpdateCancelled):self.client.prepare(fixture(),cancel=lambda:True)
        self.assertFalse(self.commits())
    def test_wrong_uid_or_session_rejected(self):
        prepared=self.client.prepare(fixture());self.port.session+=1
        with self.assertRaises(RuntimeError):self.client.commit(prepared)
        self.assertFalse(self.commits())
        self.port.uid=b'x'*12
        with self.assertRaises(RuntimeError):self.client.connect(expected_uid=UID)
    def test_reconnect_invalidates_prepared_and_changed_backup_refused(self):
        prepared=self.client.prepare(fixture());self.client.connect(expected_uid=UID)
        with self.assertRaises(RuntimeError):self.client.commit(prepared)
        self.assertFalse(self.commits())
        # New device transaction, no optimistic reuse of the previous READY.
        self.port.state=State.IDLE;self.port.received=0
        prepared=self.client.prepare(fixture());prepared.backup_path.write_bytes(b'corrupt')
        with self.assertRaises(RuntimeError):self.client.commit(prepared)
        self.assertFalse(self.commits())
    def test_lost_commit_ack_queries_status_without_resend(self):
        prepared=self.client.prepare(fixture());self.port.drop_commit=True
        self.assertTrue(self.client.commit(prepared).success)
        self.assertEqual(len(self.commits()),1)
    def test_unplug_is_unknown_never_success_or_resend(self):
        prepared=self.client.prepare(fixture());self.port.disconnect_commit=True
        result=self.client.commit(prepared)
        self.assertFalse(result.success);self.assertIn('未知',result.message)
        self.assertEqual(len(self.commits()),1)
        with self.assertRaises(RuntimeError):self.client.commit(prepared)
    def test_done_without_readback_or_wrong_crc_is_not_success(self):
        for field,value in (('done_flags',0),('done_crc',0)):
            with self.subTest(field=field):
                self.port.state=State.IDLE;self.port.received=0
                self.client=self.api.UpdaterClient(self.port,self.folder,lambda *args:None,
                    clock=lambda:self.port.now,sleep=lambda seconds:setattr(self.port,'now',self.port.now+seconds))
                self.port.done_flags=1;self.port.done_crc=None
                self.client.connect(expected_uid=UID);setattr(self.port,field,value)
                prepared=self.client.prepare(fixture())
                self.assertFalse(self.client.commit(prepared).success)
    def test_read_only_or_unverified_geometry_refused_before_begin(self):
        for field,value in (('flags',1),('sfdp',0)):
            setattr(self.port,field,value);self.client.connect(expected_uid=UID)
            with self.assertRaises(RuntimeError):self.client.prepare(fixture())
            self.assertFalse(any(f.kind==Opcode.BEGIN for f in self.port.commands))
    def test_port_filter_ignores_pwlink_and_normal_serial(self):
        from types import SimpleNamespace as S
        ports=[S(device='COM34',vid=0xd28,pid=0x204,serial_number=UID.hex()),
               S(device='COM36',vid=0xcafe,pid=0x4015,serial_number=UID.hex()),
               S(device='COM38',vid=0xcafe,pid=0x4015,serial_number='unknown')]
        self.assertEqual([p.device for p in self.api.select_devices(ports)],['COM36'])

    def test_reported_flash_error_is_failure_not_unknown(self):
        prepared=self.client.prepare(fixture());self.port.fail_commit=True
        result=self.client.commit(prepared)
        self.assertFalse(result.success);self.assertIn('更新失败',result.message)
        self.assertEqual(result.status.error,10);self.assertEqual(len(self.commits()),1)
