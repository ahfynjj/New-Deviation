"""Actual NOR command path with a fake controller and SFDP observation."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_flash_geometry import fixture
ROOT=Path(__file__).resolve().parents[3]

class NorTests(unittest.TestCase):
    def test_commands_boundaries_protection_and_timeouts(self):
        source=ROOT/'hardware/tx15/usb_update/nor.c'
        self.assertTrue(source.exists(),'Restricted NOR hardware backend missing')
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as temp:
            tmp=Path(temp);sfdp=tmp/'sfdp.bin';sfdp.write_bytes(fixture())
            exe=tmp/'nor.exe';usb=source.parent
            r=subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror',
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/lib/gcc/x86_64-w64-mingw32/16.2.0/include'),
                str(ROOT/'utils/hardware/tests/usb_nor_test.c'),str(usb/'nor_geometry.c'),
                str(usb/'transaction.c'),str(usb/'package.c'),str(ROOT/'hardware/tx15/boot/image.c'),
                '-o',str(exe)],env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stderr)
            r=subprocess.run([str(exe),str(sfdp)],env=env,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
