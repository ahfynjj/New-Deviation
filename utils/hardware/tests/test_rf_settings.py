import os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class SettingsTests(unittest.TestCase):
 def test_off_default_and_strict_protocol(self):
  gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
  env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); (p/'test.c').write_text(r"""
#include <assert.h>
#include "rf_settings.h"
int main(void) {
 struct tx15_module_setting m={0};
 assert(!tx15_module_enabled(&m));
 assert(tx15_module_parse(&m,"enabled","1"));
 assert(!tx15_module_enabled(&m));
 assert(tx15_module_parse(&m,"protocol","CRSF"));
 assert(tx15_module_enabled(&m));
 assert(!tx15_module_parse(&m,"enabled","2"));
 assert(!tx15_module_enabled(&m));
 assert(tx15_module_parse(&m,"enabled","1"));
 assert(!tx15_module_parse(&m,"protocol","unknown"));
 assert(!tx15_module_enabled(&m));
 assert(!tx15_module_parse(&m,"other","1"));
}
""")
   r=subprocess.run([str(gcc),'-std=c99','-Wall','-Werror','-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),'-I',str(ROOT/'src/target/tx/radiomaster/tx15'),str(p/'test.c'),'-o',str(p/'test.exe')],env=env,capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stderr)
   subprocess.run([str(p/'test.exe')],env=env,check=True)
