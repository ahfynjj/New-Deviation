"""Wrong board/ABI, damaged vectors, and non-product builds must never ship."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'utils'))
from hardware import boot_image
import test_app_image


def image():
    return boot_image.pack(test_app_image.AppImageTests().image())


def fixture(raw=None):
    raw = image() if raw is None else raw
    h = struct.pack('<8s6I', b'ND15UPD1', 1, 0x54583135, len(raw),
                    zlib.crc32(raw), 1, 1) + bytes(92)
    return h + struct.pack('<I', zlib.crc32(h)) + raw


def repair(raw):
    struct.pack_into('<I', raw, 124, zlib.crc32(raw[:124]))
    return raw


class USBPackageTests(unittest.TestCase):
    def setUp(self):
        try:
            self.api = importlib.import_module('usb_update.package')
        except ModuleNotFoundError:
            self.fail('USB package validator is not implemented')

    def cases(self):
        good = fixture()
        cases = [(good, True), (good + b'\0', False)]
        cases += [(good[:n], False) for n in (0, 7, 127, 128, len(good)-1)]
        for at, value in ((8, 2), (12, 0), (16, 0xffffffff), (24, 2),
                          (24, 0), (28, 2), (28, 0), (32, 1), (120, 1)):
            bad = bytearray(good)
            struct.pack_into('<I', bad, at, value)
            cases.append((repair(bad), False))
        for at in (0, 20, 124, 128, len(good)-1):
            bad = bytearray(good); bad[at] ^= 1
            cases.append((bad, False))
        # Repair every checksum after corrupting an exception vector. CRC alone
        # must not authorize an invalid ND15 execution plan.
        bad = bytearray(image())
        struct.pack_into('<I', bad, 64+8, 0x08000001)
        code_len = struct.unpack_from('<I', bad, 32)[0]
        struct.pack_into('<I', bad, 36, zlib.crc32(bad[64:64+code_len]))
        struct.pack_into('<I', bad, 60, zlib.crc32(bad[:60]))
        cases.append((fixture(bad), False))
        return cases

    def test_roundtrip_and_reject_semantic_corruption(self):
        raw = image()
        self.assertEqual(self.api.pack(raw), fixture())
        self.assertEqual(len(self.api.pack(raw)), 128+len(raw))
        for data, valid in self.cases():
            with self.subTest(length=len(data), valid=valid):
                if valid:
                    package = self.api.unpack(data)
                    self.assertEqual(package.image, raw)
                    self.assertEqual(package.image_crc, zlib.crc32(raw))
                else:
                    with self.assertRaises(ValueError): self.api.unpack(data)
        with self.assertRaises(ValueError): self.api.pack(b'not ND15')
        self.assertEqual(self.api.unpack(self.api.pack(raw, boot_api=2), boot_api=2).image, raw)

    def test_c_and_python_agree_and_c_clears_failed_plan(self):
        gcc = Path(tempfile.gettempdir()) / 'new-deviation-ucrt64/bin/gcc.exe'
        env = dict(os.environ, PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp)/'package.exe'
            cmd = [str(gcc), '-std=c99', '-Wall', '-Wextra', '-Werror',
                   '-I', str(ROOT.parent/'tools/msys64/ucrt64/include'),
                   '-I', str(ROOT.parent/'tools/msys64/ucrt64/lib/gcc/x86_64-w64-mingw32/16.2.0/include'),
                   str(ROOT/'utils/hardware/tests/usb_update_package_test.c'),
                   str(ROOT/'hardware/tx15/usb_update/package.c'),
                   str(ROOT/'hardware/tx15/boot/image.c'), '-o', str(exe)]
            run = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf8', errors='replace')
            self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
            for n,(raw, valid) in enumerate(self.cases()):
                path = Path(tmp)/f'{n}.bin'; path.write_bytes(raw)
                run = subprocess.run([str(exe), str(path), str(int(valid))], env=env,
                                     capture_output=True, text=True, encoding='utf8', errors='replace')
                self.assertEqual(run.returncode, 0, run.stdout+run.stderr)

    def test_cli_only_packs_matching_product_build(self):
        elf = bytes(test_app_image.AppImageTests().image()); payload = image()
        with tempfile.TemporaryDirectory(prefix='USB 中文 ') as tmp:
            folder = Path(tmp); output = folder/'release.ndu'
            (folder/'tx15-app.elf').write_bytes(elf)
            (folder/'tx15-app.nd15').write_bytes(payload)
            meta = dict(schema=1, mode='standalone-elrs-candidate', rf_enabled=True,
                        persistent_settings=True, elf_sha256=hashlib.sha256(elf).hexdigest(),
                        payload_sha256=hashlib.sha256(payload).hexdigest())
            command = [sys.executable, str(ROOT/'utils/pack-tx15-update.py'),
                       '--build', str(folder), '--output', str(output)]
            for field, value in ((None,None), ('rf_enabled',False),
                                 ('persistent_settings',False), ('elf_sha256','bad'),
                                 ('payload_sha256','bad'), ('mode','ram-bench')):
                m = dict(meta)
                if field: m[field] = value
                (folder/'build.json').write_text(json.dumps(m), encoding='utf8')
                output.unlink(missing_ok=True)
                run = subprocess.run(command, capture_output=True, text=True)
                if field is None:
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(output.read_bytes(), fixture())
                else:
                    self.assertNotEqual(run.returncode, 0)
                    self.assertFalse(output.exists())
