import os, subprocess, tempfile, unittest
from pathlib import Path
class InputTests(unittest.TestCase):
 def test_debounce_rotation_and_invalid_transitions(self):
  root=Path(__file__).resolve().parents[3]
  gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
  with tempfile.TemporaryDirectory() as tmp:
   src=Path(tmp)/'input.c';exe=Path(tmp)/'input.exe'
   src.write_text(r"""
#include <assert.h>
#include "hardware/tx15/board/inputs.h"
int main(void) {
 struct tx15_input_filter f={0}; struct tx15_input_event e;
 tx15_input_filter_init(&f,0,3);
 for(int i=0;i<19;i++) { e=tx15_input_filter_step(&f,1,3); assert(!e.pressed); }
 e=tx15_input_filter_step(&f,1,3); assert(e.pressed==1);
 for(int i=0;i<100;i++) assert(!tx15_input_filter_step(&f,1,3).pressed);
 for(int i=0;i<20;i++) tx15_input_filter_step(&f,0,3);
 for(int i=0;i<10;i++) { assert(!tx15_input_filter_step(&f,1,3).pressed); tx15_input_filter_step(&f,0,3); }
 const unsigned phase[]={1,0,2,3}; int sum=0;
 for(int i=0;i<4;i++) sum+=tx15_input_filter_step(&f,0,phase[i]).rotation;
 assert(sum==1);
 const unsigned reverse[]={2,0,1,3}; sum=0;
 for(int i=0;i<4;i++) sum+=tx15_input_filter_step(&f,0,reverse[i]).rotation;
 assert(sum==-1);
 assert(!tx15_input_filter_step(&f,0,0).rotation);
 assert(!tx15_input_filter_step(&f,0,3).rotation);
 /* A key already held at startup must be released before generating a press. */
 tx15_input_filter_init(&f,1,3);
 for(int i=0;i<25;i++) assert(!tx15_input_filter_step(&f,1,3).pressed);
 return 0;
}
""")
   env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
   subprocess.run([str(gcc),'-I',str(gcc.parent.parent/'include'),'-I',str(root),str(src),str(root/'hardware/tx15/board/input_filter.c'),'-o',str(exe)],check=True,env=env,capture_output=True)
   subprocess.run([str(exe)],check=True,env=env)
