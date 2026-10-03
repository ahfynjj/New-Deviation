import os, subprocess, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class BootQspiTests(unittest.TestCase):
    def test_read_only_commands_clock_pin_scope_and_timeouts(self):
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'boot-qspi.exe'
            result=subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror',
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),'-I',str(ROOT),
                str(ROOT/'utils/hardware/tests/boot_qspi_test.c'),'-o',str(exe)],
                env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            result=subprocess.run([str(exe)],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
