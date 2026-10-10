"""A COMMIT freezes RAM before any service callback and cannot be replayed."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_usb_update_package import fixture,ROOT


class USBRuntimeTests(unittest.TestCase):
    def test_commit_identity_and_mutation_during_service(self):
        self.assertTrue((ROOT/'hardware/tx15/usb_update/runtime.c').exists(),'USB commit dispatcher missing')
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'runtime.exe';p=Path(tmp)/'package.ndu';p.write_bytes(fixture())
            r=subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror',
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/lib/gcc/x86_64-w64-mingw32/16.2.0/include'),
                str(ROOT/'utils/hardware/tests/usb_runtime_test.c'),
                *[str(ROOT/'hardware/tx15/usb_update'/s) for s in ('transaction.c','package.c','protocol.c','receiver.c','runtime.c')],
                str(ROOT/'hardware/tx15/boot/image.c'),'-o',str(exe)],env=env,
                capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stderr)
            r=subprocess.run([str(exe),str(p)],env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
