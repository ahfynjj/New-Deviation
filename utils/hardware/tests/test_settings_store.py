import os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class StoreTests(unittest.TestCase):
 def test_torn_write_keeps_previous_and_checks_corruption(self):
  gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
  env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.c').write_text(r"""
#include <assert.h>
#include <string.h>
#include "settings_store.h"
#include "settings_clock.h"
static unsigned char flash[65536],backup[65536];
static int budget=-1,fail_read=-1;
static unsigned erases,programs;
static int read_flash(void *c,unsigned a,void *p,unsigned n) {(void)c;if(fail_read>=0 && a==(unsigned)fail_read)return 0;if(a+n>sizeof(flash))return 0;memcpy(p,flash+a,n);return 1;}
static int erase(void *c,unsigned a) {(void)c;erases++;if(a!=0 && a!=32768)return 0;memset(flash+a,255,32768);return 1;}
static int program(void *c,unsigned a,const void *p,unsigned n) {
 (void)c;programs++;const unsigned char *v=p;
 for(unsigned i=0;i<n;i++){if(!budget)return 0;if(budget>0)budget--;flash[a+i]&=v[i];}return 1;
}
int main(void) {
 assert(tx15_settings_core_clock(0x03030005));
 assert(tx15_settings_core_clock(0x33030005));
 assert(!tx15_settings_core_clock(0x13030005));
 assert(!tx15_settings_core_clock(0x33030001));
 struct tx15_store_io io={0,read_flash,erase,program};unsigned char out[64],old[64],next[64];
 memset(flash,255,sizeof(flash));memset(old,21,sizeof(old));memset(next,42,sizeof(next));
 assert(!tx15_store_load(&io,1,out,sizeof(out)));
 assert(tx15_store_save(&io,1,old,sizeof(old)));
 assert(tx15_store_load(&io,1,out,sizeof(out)) && !memcmp(out,old,64));
 memcpy(backup,flash,sizeof(flash));
 for(unsigned a=0;a<2;a++) {
  unsigned e=erases,p=programs;fail_read=a?32:0;
  assert(!tx15_store_save(&io,1,next,64));
  assert(erases==e && programs==p);fail_read=-1;
 }
 for(int cut=0;cut<100;cut++) {
  memcpy(flash,backup,sizeof(flash));budget=cut;
  int ok=tx15_store_save(&io,1,next,sizeof(next));budget=-1;
  assert(tx15_store_load(&io,1,out,64));
  assert(!memcmp(out,ok?next:old,64));
 }
 memcpy(flash,backup,sizeof(flash));assert(tx15_store_save(&io,1,next,64));
 flash[32768+32]^=1;
 assert(tx15_store_load(&io,1,out,64) && !memcmp(out,old,64));
 assert(!tx15_store_load(&io,2,out,64));
 assert(!tx15_store_load(&io,1,out,63));
}
""")
   r=subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror','-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),'-I',str(ROOT/'hardware/tx15/board'),str(p/'test.c'),str(ROOT/'hardware/tx15/board/settings_store.c'),'-o',str(p/'test.exe')],env=env,capture_output=True,text=True,encoding="utf8",errors="replace")
   self.assertEqual(r.returncode,0,r.stderr)
   subprocess.run([str(p/'test.exe')],env=env,check=True)
