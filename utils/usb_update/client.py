"""Dedicated updater transport and durable backup. No implicit device access."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import time
import uuid
from .package import unpack
from .protocol import Frame,FrameCodec,Opcode,DeviceInfo,DeviceStatus,State,encode

class UpdateCancelled(RuntimeError):pass

@dataclass(frozen=True)
class PreparedUpdate:
    uid: bytes
    session: int
    image_bytes: int
    image_crc: int
    backup_path: Path
    backup_sha256: str
    metadata_path: Path

@dataclass(frozen=True)
class UpdateResult:
    success: bool
    message: str
    status: DeviceStatus | None = None
    backup_path: Path | None = None

def select_devices(ports):
    return [p for p in ports if p.vid==0xcafe and p.pid==0x4015
            and re.fullmatch(r'[0-9a-fA-F]{24}',p.serial_number or '')]

def _atomic(path,data):
    temporary=path.with_name(path.name+'.tmp')
    try:
        with temporary.open('xb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temporary,path)
        if path.read_bytes()!=data:raise OSError('备份落盘读回不一致')
    finally:
        temporary.unlink(missing_ok=True)

def save_backup(folder,uid,session,data):
    if len(data)!=65536:raise ValueError('模型和校准备份长度不完整')
    folder=Path(folder)/uid.hex();folder.mkdir(parents=True,exist_ok=True)
    stem=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:12]
    binary=folder/(stem+'.bin');metadata=folder/(stem+'.json')
    digest=hashlib.sha256(data).hexdigest()
    _atomic(binary,data)
    record=dict(schema=1,uid=uid.hex(),session=session,offset=0xf0000,
                bytes=65536,sha256=digest,file=binary.name)
    _atomic(metadata,(json.dumps(record,indent=2)+'\n').encode('utf8'))
    return binary,metadata,digest

class UpdaterClient:
    def __init__(self,transport,backup_dir,progress=lambda *args:None,*,clock=time.monotonic,sleep=time.sleep):
        self.transport=transport;self.backup_dir=Path(backup_dir);self.progress=progress
        self.clock=clock;self.sleep=sleep;self.codec=FrameCodec()
        self.info=None;self.sequence=1;self._prepared=None;self._commit_sent=False

    def _exchange(self,frame,timeout=8):
        deadline=self.clock()+timeout;data=encode(frame);written=0
        while written<len(data):
            if self.clock()>=deadline:raise TimeoutError('USB 发送超时')
            n=self.transport.write(data[written:])
            if not isinstance(n,int) or not 0<=n<=len(data)-written:raise OSError('USB 写入长度异常')
            written+=n
            if not n:self.sleep(.01)
        while self.clock()<deadline:
            for response in self.codec.feed(self.transport.read(1056)):
                if response.kind==(frame.kind|0x80) and response.sequence==frame.sequence:
                    if response.offset!=frame.offset:raise RuntimeError('USB 返回偏移不一致')
                    if frame.kind!=Opcode.HELLO and response.session!=frame.session:
                        raise RuntimeError('USB 会话已改变，请重新连接和准备')
                    return response
        raise TimeoutError('USB 应答超时')

    def _hello(self):
        info=DeviceInfo.from_frame(self._exchange(Frame(Opcode.HELLO,0,0,0)))
        if len(info.uid)!=12 or info.uid in (bytes(12),b'\xff'*12):raise RuntimeError('遥控器身份无效')
        return info

    def connect(self,expected_uid=None):
        self._prepared=None;self.info=None;self.codec=FrameCodec();self.sequence=1
        info=self._hello()
        if expected_uid is not None and info.uid!=expected_uid:raise RuntimeError('USB 设备与遥控器身份不一致')
        self.info=info
        # A reconnect must not authorize a second COMMIT on this client instance.
        return info

    def _send(self,kind,payload=b'',offset=0,timeout=8):
        if self.info is None:raise RuntimeError('请先连接遥控器')
        frame=Frame(kind,self.info.session,self.sequence,offset,payload);self.sequence+=1
        return self._exchange(frame,timeout)

    def _control(self,kind,payload=b'',offset=0,timeout=8):
        status=DeviceStatus.from_payload(self._send(kind,payload,offset,timeout).payload)
        if status.error:raise RuntimeError(f'遥控器拒绝操作：错误 {status.error}')
        return status

    def status(self):return DeviceStatus.from_payload(self._send(Opcode.STATUS).payload)

    @staticmethod
    def _writable(info):
        return info.flags==2 and info.write_observed and info.sfdp_valid==1 \
            and (info.jedec,info.capacity,info.page_bytes,info.erase_bytes)==(0xc84018,0x1000000,256,4096) \
            and not info.sr1 and not info.sr2&~2 and not info.sr3&~0x60

    def prepare(self,raw,*,cancel=lambda:False):
        self._prepared=None
        if self.info is None or self._commit_sent:raise RuntimeError('请重新启动更新工具并连接遥控器')
        package=unpack(raw,boot_api=self.info.boot_api,settings_abi=self.info.settings_abi)
        if not self._writable(self.info) or len(package.image)>self.info.max_image_bytes:
            raise RuntimeError('设备为只读、未同步或 Flash 规格未核对，禁止更新')
        def check_cancel():
            if cancel():raise UpdateCancelled('已取消，未提交写入')
        backup=bytearray()
        for offset in range(0,65536,1024):
            check_cancel();response=self._send(Opcode.READ_SETTINGS,struct.pack('<I',1024),offset)
            if len(response.payload)!=1024:raise RuntimeError('模型和校准读取失败，不提交更新')
            backup.extend(response.payload);self.progress('backup',offset+1024,65536)
        check_cancel()
        path,metadata,digest=save_backup(self.backup_dir,self.info.uid,self.info.session,bytes(backup))
        check_cancel();self.sequence=1
        self._control(Opcode.BEGIN,raw[:128])
        for offset in range(0,len(package.image),1024):
            check_cancel();status=self._control(Opcode.DATA,package.image[offset:offset+1024],offset)
            if status.received!=min(offset+1024,len(package.image)):
                raise RuntimeError('固件接收进度不一致')
            self.progress('receive',status.received,len(package.image))
        status=self._control(Opcode.FINALIZE,timeout=15)
        if status.state!=State.READY or status.total!=len(package.image) or status.image_crc!=package.image_crc:
            raise RuntimeError('完整固件未通过遥控器校验')
        check_cancel()
        prepared=PreparedUpdate(self.info.uid,self.info.session,len(package.image),package.image_crc,path,digest,metadata)
        self._prepared=prepared;return prepared

    def commit(self,prepared,*,timeout=120):
        if self._commit_sent or self._prepared is not prepared or self.info is None:
            raise RuntimeError('准备结果已失效，不能重复提交')
        latest=self._hello()
        if (latest.uid,latest.session)!=(prepared.uid,prepared.session) or not self._writable(latest):
            self._prepared=None;raise RuntimeError('设备、会话或写入状态已改变，禁止提交')
        data=prepared.backup_path.read_bytes()
        metadata=json.loads(prepared.metadata_path.read_text(encoding='utf8'))
        if len(data)!=65536 or hashlib.sha256(data).hexdigest()!=prepared.backup_sha256 \
            or metadata!=dict(schema=1,uid=prepared.uid.hex(),session=prepared.session,offset=0xf0000,
                bytes=65536,sha256=prepared.backup_sha256,file=prepared.backup_path.name):
            raise RuntimeError('模型和校准备份被改变，禁止提交')
        status=self.status()
        if status.error or status.state!=State.READY or status.image_crc!=prepared.image_crc or status.total!=prepared.image_bytes:
            raise RuntimeError('遥控器已校验的固件与准备结果不一致')
        self._commit_sent=True;self._prepared=None;deadline=self.clock()+timeout
        try:
            try:status=DeviceStatus.from_payload(self._send(Opcode.COMMIT,
                prepared.uid+struct.pack('<2I',prepared.image_bytes,prepared.image_crc),timeout=15).payload)
            except TimeoutError:status=None # Only STATUS from here; never resend COMMIT.
            while self.clock()<deadline:
                if status is not None:
                    self.progress('write',status.received,status.total)
                    if status.state==State.DONE:
                        verified=status.verified_done and status.verification_flags==1 \
                            and (status.total,status.received,status.image_crc)==(prepared.image_bytes,prepared.image_bytes,prepared.image_crc)
                        return UpdateResult(verified,'更新完成，请关闭并重新开机' if verified else '完成反馈未通过读回核对',status,prepared.backup_path)
                    if status.error or status.state==State.ERROR:
                        return UpdateResult(False,f'更新失败：错误 {status.error}',status,prepared.backup_path)
                    if status.state not in (State.VALIDATING,State.ERASING,State.PROGRAMMING,State.VERIFYING):
                        return UpdateResult(False,'更新状态异常，未确认完成',status,prepared.backup_path)
                self.sleep(.1)
                try:status=self.status()
                except TimeoutError:status=None
            return UpdateResult(False,'更新状态未知：等待超时。保持供电，不能重复提交',backup_path=prepared.backup_path)
        except (OSError,RuntimeError,ValueError) as exc:
            return UpdateResult(False,f'更新状态未知：{exc}。保持供电，不能重复提交',backup_path=prepared.backup_path)

    def close(self):self._prepared=None;self.info=None;self.transport.close()
