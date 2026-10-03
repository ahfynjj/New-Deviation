import os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class RfModelTests(unittest.TestCase):
 def test_default_off_switch_reset_and_session_timeout(self):
  gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
  env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
  with tempfile.TemporaryDirectory() as tmp:
   exe=Path(tmp)/'rfmodel.exe'
   includes=[]
   for d in ('','src','src/target/tx/radiomaster/tx15','src/target/drivers/filesystems','src/gui/320x240x16','src/pages/320x240x16'):
    includes+=['-I',str(ROOT/d)]
   cmd=[str(gcc),'-std=c99','-Wall','-Wextra','-Werror','-DTX15_ELRS_RC=1','-DUSE_OWN_PRINTF=0',
    '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),*includes,
    str(ROOT/'utils/hardware/tests/rf_model_test.c'),
    str(ROOT/'src/target/tx/radiomaster/tx15/rf_model.c'),'-o',str(exe)]
   result=subprocess.run(cmd,env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   subprocess.run([str(exe)],env=env,check=True,timeout=10)
