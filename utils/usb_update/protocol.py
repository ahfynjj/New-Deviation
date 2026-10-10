"""Bounded native CDC framing and typed device replies."""
from dataclasses import dataclass
from enum import IntEnum
import struct
import zlib

MAX_PAYLOAD = 1024


class Opcode(IntEnum):
    HELLO=1; BEGIN=2; DATA=3; FINALIZE=4; STATUS=5; READ_SETTINGS=6; COMMIT=7; ABORT=8


class State(IntEnum):
    IDLE=0; RECEIVING=1; VALIDATING=2; READY=3; ERASING=4
    PROGRAMMING=5; VERIFYING=6; DONE=7; ERROR=8


@dataclass(frozen=True)
class Frame:
    kind: int
    session: int
    sequence: int
    offset: int
    payload: bytes = b''


def encode(frame: Frame) -> bytes:
    if len(frame.payload) > MAX_PAYLOAD:
        raise ValueError('Frame payload too large')
    try:
        h = struct.pack('<4sBBHQIII',b'NDU1',1,frame.kind,0,frame.session,
                        frame.sequence,frame.offset,len(frame.payload))
    except struct.error as exc:
        raise ValueError('Invalid frame field') from exc
    return h+struct.pack('<I',zlib.crc32(h+frame.payload))+frame.payload


class FrameCodec:
    def __init__(self):
        self._buffer = bytearray()

    @property
    def buffered_bytes(self): return len(self._buffer)

    def feed(self, data: bytes) -> list[Frame]:
        frames=[]
        # Consume bytewise: never allocate unbounded input into the parser.
        for byte in data:
            self._buffer.append(byte)
            while len(self._buffer)>=4:
                b=self._buffer
                if b[:4]!=b'NDU1': del b[0]; continue
                if len(b)<32: break
                _,version,kind,flags,session,sequence,offset,size,crc=struct.unpack_from('<4sBBHQIIII',b)
                if version!=1 or flags or size>MAX_PAYLOAD: del b[0]; continue
                if len(b)<32+size: break
                payload=bytes(b[32:32+size])
                if zlib.crc32(bytes(b[:28])+payload)!=crc: del b[0]; continue
                del b[:32+size]
                frames.append(Frame(kind,session,sequence,offset,payload))
        return frames


@dataclass(frozen=True)
class DeviceInfo:
    uid: bytes
    session: int
    boot_api: int
    settings_abi: int
    max_image_bytes: int
    flags: int
    jedec: int
    capacity: int
    page_bytes: int
    erase_bytes: int
    sr1: int
    sr2: int
    sr3: int
    sfdp_valid: int

    @property
    def read_only(self): return bool(self.flags & 1)

    @property
    def write_observed(self): return bool(self.flags & 2) and not self.read_only

    @classmethod
    def from_frame(cls, frame):
        if frame.kind!=0x81 or len(frame.payload)!=48 or not frame.session:
            raise ValueError('Invalid device HELLO')
        return cls(frame.payload[:12],frame.session,*struct.unpack_from('<8I4B',frame.payload,12))


@dataclass(frozen=True)
class DeviceStatus:
    state: State
    error: int
    received: int
    total: int
    image_crc: int
    verification_flags: int

    @property
    def verified_done(self):
        return self.state==State.DONE and not self.error and bool(self.verification_flags&1)

    @classmethod
    def from_payload(cls, payload):
        if len(payload)!=24: raise ValueError('Invalid status length')
        state,*fields=struct.unpack('<6I',payload)
        return cls(State(state),*fields)
