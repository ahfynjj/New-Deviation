import os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class ExternalTests(unittest.TestCase):
 def test_power_inversion_and_tx_to_rx_turnaround(self):
  gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
  env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);exe=p/'test.exe'
   cmd=[str(gcc),'-std=c99','-Wall','-Wextra','-Werror','-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),'-I',str(ROOT),str(ROOT/'utils/hardware/tests/rf_external_test.c'),'-o',str(exe)]
   r=subprocess.run(cmd,env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
   self.assertEqual(r.returncode,0,r.stderr)
   subprocess.run([str(exe)],env=env,check=True)
