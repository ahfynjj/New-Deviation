"""Actual Boot_Main fault routing with replaced peripheral/assembly seams."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[3]

class BootMainTests(unittest.TestCase):
    def test_qspi_faults_are_read_only_and_normal_route_survives(self):
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'boot.exe'
            r=subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror',
                '-Wno-int-to-pointer-cast','-Wno-unused-but-set-variable',
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),
                str(ROOT/'utils/hardware/tests/usb_boot_main_test.c'),'-o',str(exe)],
                env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stderr)
            r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
