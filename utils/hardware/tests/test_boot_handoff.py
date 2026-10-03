import os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class HandoffTests(unittest.TestCase):
    def test_rejects_incomplete_or_wrong_boot_contract_and_handles_power_key(self):
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'handoff.exe'
            r=subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror','-I',str(ROOT),
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),str(ROOT/'utils/hardware/tests/boot_handoff_test.c'),
                str(ROOT/'hardware/tx15/boot/handoff.c'),str(ROOT/'hardware/tx15/boot/power_button.c'),'-o',str(exe)],
                env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
