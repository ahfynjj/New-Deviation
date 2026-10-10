"""Replay, stream noise and offset wrap cannot mutate a frozen RAM image."""
import importlib
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from test_usb_update_package import fixture, image, ROOT


def wire(kind, payload=b'', *, session=123, sequence=1, offset=0):
    h = struct.pack('<4sBBHQIII', b'NDU1', 1, kind, 0, session, sequence, offset, len(payload))
    return h+struct.pack('<I', zlib.crc32(h+payload))+payload


class USBProtocolTests(unittest.TestCase):
    def setUp(self):
        try: self.api = importlib.import_module('usb_update.protocol')
        except ModuleNotFoundError: self.fail('Bounded USB frame codec is missing')

    def test_stream_split_merge_noise_and_length_overflow(self):
        a = wire(1, session=0, sequence=0); b = wire(3, bytes(range(256)), sequence=2)
        for split in range(len(a+b)+1):
            codec = self.api.FrameCodec()
            frames = codec.feed((a+b)[:split])+codec.feed((a+b)[split:])
            self.assertEqual([f.kind for f in frames], [1,3])
            self.assertEqual(frames[1].payload, bytes(range(256)))
            self.assertEqual(self.api.encode(frames[1]), b)
        bad = bytearray(a); bad[28] ^= 1
        long = bytearray(a); struct.pack_into('<I', long, 24, 0xffffffff)
        codec = self.api.FrameCodec()
        decoded = codec.feed(b'garbageNDU'+bytes(long)+bytes(bad)+a+b)
        self.assertEqual([f.kind for f in decoded], [1,3])
        self.assertLessEqual(codec.buffered_bytes, 1056)
        with self.assertRaises(ValueError): self.api.encode(self.api.Frame(3,123,1,0,bytes(1025)))

    def test_device_payloads_reject_wrong_length_and_invalid_states(self):
        hello = bytes.fromhex('1c0039000e51333234363236')+struct.pack('<8I4B',1,1,0xec040,1,
                    0xc84018,0x1000000,256,4096,0,0,0,1)
        info = self.api.DeviceInfo.from_frame(self.api.Frame(0x81,123,0,0,hello))
        self.assertEqual(info.uid.hex(),'1c0039000e51333234363236')
        self.assertEqual(info.session,123)
        self.assertTrue(info.read_only)
        status = self.api.DeviceStatus.from_payload(struct.pack('<6I',7,0,800,800,7,1))
        self.assertTrue(status.verified_done)
        for raw in (b'', bytes(25), struct.pack('<6I',9,0,0,0,0,0)):
            with self.assertRaises(ValueError): self.api.DeviceStatus.from_payload(raw)

    def run_receiver(self, commands, *, capacity=0xec0c0):
        gcc = Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env = dict(os.environ, PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp)/'receiver.exe'; path = Path(tmp)/'commands.bin'
            cmd = [str(gcc),'-std=c99','-Wall','-Wextra','-Werror',
                   '-I', str(ROOT.parent/'tools/msys64/ucrt64/include'),
                   '-I', str(ROOT.parent/'tools/msys64/ucrt64/lib/gcc/x86_64-w64-mingw32/16.2.0/include'),
                   str(ROOT/'utils/hardware/tests/usb_update_receiver_test.c'),
                   *[str(ROOT/'hardware/tx15/usb_update'/s) for s in ('package.c','protocol.c','receiver.c')],
                   str(ROOT/'hardware/tx15/boot/image.c'), '-o', str(exe)]
            r = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf8', errors='replace')
            self.assertEqual(r.returncode,0,r.stderr)
            data = b''
            for kind,body in commands:
                data += struct.pack('<BI',kind,len(body))+body
            path.write_bytes(data)
            r = subprocess.run([str(exe),str(path),str(capacity)], env=env, capture_output=True,
                               text=True, encoding='utf8', errors='replace')
            self.assertEqual(r.returncode,0,r.stderr)
            return [list(map(int,line.split())) for line in r.stdout.splitlines()]

    def test_receiver_replay_gap_timeout_and_ready_immutable(self):
        raw = image(); begin = wire(2,fixture()[:128]); data = wire(3,raw,sequence=2)
        done = wire(4,sequence=3)
        commands = [(1,begin),(1,wire(3,raw,session=122,sequence=2)),
                    (1,wire(3,raw,sequence=3)),(1,wire(3,raw,sequence=2,offset=0xffffffff)),
                    (1,data),(1,data),(1,wire(3,raw[:-1]+b'x',sequence=2)),(1,done),
                    (1,begin),(1,data),(1,done),(1,wire(7,bytes(12)+struct.pack('<2I',len(raw),zlib.crc32(raw)),sequence=4)),
                    (1,wire(8,sequence=4)),(1,begin)]
        rows = self.run_receiver(commands)
        self.assertEqual([r[0] for r in rows],[1,0,0,0,1,1,0,1,0,0,1,1,1,0])
        self.assertEqual(rows[7][1],3)  # READY
        self.assertEqual(rows[7][3],len(raw))
        self.assertEqual(rows[12][1],0)  # ABORT clears authorization/session
        timeout = self.run_receiver([(1,begin),(2,struct.pack('<I',30000)),(1,data)])
        self.assertEqual(timeout[-1][0],0)
        self.assertEqual(timeout[-1][1],8)
        # Sequence exhaustion cannot wrap and authorize a new transfer.
        rows = self.run_receiver([(1,wire(2,fixture()[:128],sequence=0xffffffff)),(1,begin),
                                  (1,wire(3,raw,sequence=0)),(1,data)])
        self.assertEqual([r[0] for r in rows],[0,1,0,1])
        rows = self.run_receiver([(1,begin)],capacity=128)
        self.assertEqual(rows[0][0],0)

    def test_c_stream_noise_crc_and_absolute_timeout(self):
        bad = bytearray(wire(1,session=0)); bad[28] ^= 1
        rows = self.run_receiver([(1,bytes(bad)+b'noise'+wire(2,fixture()[:128]))])
        self.assertEqual(len(rows),1)
        raw = image()
        # Keep data arriving within 30s but exceed the five-minute total budget.
        commands = [(1,wire(2,fixture()[:128]))]
        for seq in range(2,14):
            commands += [(2,struct.pack('<I',(seq-1)*25000)),
                         (1,wire(3,raw[seq-2:seq-1],sequence=seq,offset=seq-2))]
        rows = self.run_receiver(commands)
        self.assertEqual(rows[-1][0],0)
        self.assertEqual(rows[-1][1],8)

    def test_maximum_image_fits_exact_capacity_and_rejects_extra_byte(self):
        code = bytearray(0x6c000)
        struct.pack_into('<176I',code,0,0x24080000,*([0x240102c1]*175))
        resources = bytes(0x80000)
        header = struct.pack('<8s13I',b'ND15APP1',1,0xec040,0x240102c1,0x54583135,
                             0x24010000,64,len(code),zlib.crc32(code),
                             0xd0080000,64+len(code),len(resources),zlib.crc32(resources),0)
        raw=header+struct.pack('<I',zlib.crc32(header))+code+resources
        commands=[(1,wire(2,fixture(raw)[:128]))]
        seq=2
        for offset in range(0,len(raw),1024):
            commands.append((1,wire(3,raw[offset:offset+1024],sequence=seq,offset=offset)))
            seq+=1
        commands.extend([(1,wire(3,b'x',sequence=seq,offset=len(raw))),
                         (1,wire(4,sequence=seq))])
        rows=self.run_receiver(commands,capacity=128+len(raw))
        self.assertEqual(rows[-2][0],0)
        self.assertEqual(rows[-1][:2],[1,3])
        self.assertEqual(rows[-1][3],0xec040)
