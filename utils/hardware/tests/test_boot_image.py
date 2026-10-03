import os, struct, subprocess, sys, tempfile, unittest, zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from boot_image import pack, unpack
import test_app_image

ROOT=Path(__file__).resolve().parents[3]

class BootImageTests(unittest.TestCase):
    def image(self):
        return pack(test_app_image.AppImageTests().image())

    def test_roundtrip_and_deterministic(self):
        raw=self.image()
        entry,segments=unpack(raw)
        self.assertEqual(entry,0x240102c1)
        self.assertEqual([a for a,b in segments],[0x24010000,0xd0080000])
        self.assertEqual(raw,self.image())

    def test_package_import_used_by_app_builder(self):
        result=subprocess.run([sys.executable,'-c',
            'import sys; sys.path.insert(0,"utils"); from hardware.boot_image import pack'],
            cwd=ROOT,capture_output=True,text=True,encoding='utf8',errors='replace')
        self.assertEqual(result.returncode,0,result.stderr)

    def test_truncated_app_and_invalid_elf_rejected(self):
        with self.assertRaises(ValueError): pack(b'not ELF')
        raw=self.image()
        for n in (0,7,63,64,len(raw)-1):
            with self.assertRaises(ValueError): unpack(raw[:n])

    def test_corrupt_header_payload_and_padding_rejected(self):
        raw=self.image()
        for at in (0,8,16,60,64,len(raw)-1):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError): unpack(bad)
        elf=test_app_image.AppImageTests().image()
        struct.pack_into('<I',elf,52+16,709) # three padding bytes
        raw=bytearray(pack(elf));raw[64+710]=1
        with self.assertRaises(ValueError): unpack(raw)

    def test_semantic_mutations_rejected_even_with_valid_header_crc(self):
        for at,value in ((8,2),(20,0),(24,0x08000000),(28,0),(32,0xffffffff),
                         (40,0x24010000),(44,64),(48,0xffffffff),(56,1),(16,0x240102c0)):
            bad=bytearray(self.image());struct.pack_into('<I',bad,at,value)
            struct.pack_into('<I',bad,60,zlib.crc32(bad[:60]))
            with self.assertRaises(ValueError): unpack(bad)

    def test_vectors_rejected_even_after_payload_crc_recomputed(self):
        for at,value in ((64,0x20020000),(68,0x240102c3),(72,0x08000001)):
            bad=bytearray(self.image());struct.pack_into('<I',bad,at,value)
            code_len=struct.unpack_from('<I',bad,32)[0]
            struct.pack_into('<I',bad,36,zlib.crc32(bad[64:64+code_len]))
            struct.pack_into('<I',bad,60,zlib.crc32(bad[:60]))
            with self.assertRaises(ValueError): unpack(bad)

    def test_firmware_c_validator_matches_host_and_no_partial_plan(self):
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'boot-image-test.exe'
            result=subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror',
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/lib/gcc/x86_64-w64-mingw32/16.2.0/include'),
                str(ROOT/'utils/hardware/tests/boot_image_test.c'),
                str(ROOT/'hardware/tx15/boot/image.c'),'-o',str(exe)],
                env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            images=[(self.image(),True)]
            for at in (0,8,12,16,20,24,28,32,36,40,44,48,52,56,60,64,68,72):
                bad=bytearray(self.image());bad[at]^=1
                # Repair checksums to exercise the semantic checks too.
                if at>=64:
                    n=struct.unpack_from('<I',bad,32)[0]
                    struct.pack_into('<I',bad,36,zlib.crc32(bad[64:64+n]))
                struct.pack_into('<I',bad,60,zlib.crc32(bad[:60]))
                try: unpack(bad); valid=True
                except ValueError: valid=False
                images.append((bad,valid))
            images.extend((self.image()[:n],False) for n in (0,63,64,len(self.image())-1))
            for i,(raw,valid) in enumerate(images):
                path=Path(tmp)/f'{i}.bin';path.write_bytes(raw)
                run=subprocess.run([str(exe),str(path),'1' if valid else '0'],env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
                self.assertEqual(run.returncode,0,run.stdout+run.stderr)

if __name__=='__main__': unittest.main()
