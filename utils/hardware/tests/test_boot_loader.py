import os,struct,subprocess,sys,tempfile,unittest,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from boot_image import pack
import test_app_image

class BootLoaderTests(unittest.TestCase):
    def test_full_transaction_and_no_entry_after_read_validation_copy_or_readback_failure(self):
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'loader.exe'
            r=subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror','-I',str(ROOT),
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/lib/gcc/x86_64-w64-mingw32/16.2.0/include'),
                str(ROOT/'utils/hardware/tests/boot_loader_test.c'),str(ROOT/'hardware/tx15/boot/loader.c'),
                str(ROOT/'hardware/tx15/boot/image.c'),'-o',str(exe)],env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            raw=pack(test_app_image.AppImageTests().image())
            cases=[(raw,m) for m in range(4)]
            for at,value in [(0,0),(8,2),(12,0xffffffff),(24,0x08000000),(32,0x6c008),(56,1)]:
                bad=bytearray(raw);struct.pack_into('<I',bad,at,value)
                struct.pack_into('<I',bad,60,zlib.crc32(bad[:60]));cases.append((bad,4))
            bad=bytearray(raw);bad[-1]^=1;cases.append((bad,4))
            bad=bytearray(raw);bad[72]^=1;cases.append((bad,4))
            for i,(data,mode) in enumerate(cases):
                path=Path(tmp)/f'case-{i}.nd15';path.write_bytes(data)
                r=subprocess.run([str(exe),str(path),str(mode)],env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
                self.assertEqual(r.returncode,0,f'case {i}: {r.stdout}{r.stderr}')

if __name__=='__main__':unittest.main()
