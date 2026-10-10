"""Every NOR failure prevents DONE; settings and the whole untouched tail survive."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_usb_update_package import fixture, ROOT


class USBTransactionTests(unittest.TestCase):
    def test_header_last_failure_injection_and_preserved_tail(self):
        self.assertTrue((ROOT/'hardware/tx15/usb_update/transaction.c').exists(),
                        'Bounded USB NOR transaction is missing')
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'transaction.exe';package=Path(tmp)/'package.ndu';package.write_bytes(fixture())
            r=subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror',
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/lib/gcc/x86_64-w64-mingw32/16.2.0/include'),
                str(ROOT/'utils/hardware/tests/usb_update_transaction_test.c'),
                *[str(ROOT/'hardware/tx15/usb_update'/s) for s in ('transaction.c','package.c')],
                str(ROOT/'hardware/tx15/boot/image.c'),'-o',str(exe)],env=env,
                capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stderr)
            r=subprocess.run([str(exe),str(package)],env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
