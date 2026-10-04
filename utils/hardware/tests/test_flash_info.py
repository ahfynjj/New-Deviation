import os
import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class FlashInfoTests(unittest.TestCase):
    def test_actual_c_reader_emits_only_status_and_sfdp_commands(self):
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'info.exe'
            p=subprocess.run([str(gcc),'-std=c11','-Wall','-Wextra','-Werror',
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),'-I',str(ROOT),
                str(ROOT/'utils/hardware/tests/flash_info_test.c'),'-o',str(exe)],
                env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            p=subprocess.run([str(exe)],env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)

