import os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class SnapshotTests(unittest.TestCase):
 def test_layout_calibration_validation_and_mode(self):
  gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
  env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ['PATH'])
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.c').write_text(r"""
#include <assert.h>
#include "settings_snapshot.h"
int main(void) {
 struct tx15_snapshot_header h={0};
 assert(!tx15_snapshot_valid(&h,100));
 h.magic=TX15_SNAPSHOT_MAGIC;h.version=1;h.model_bytes=100;h.mode=2;
 assert(tx15_snapshot_valid(&h,100));assert(!tx15_snapshot_valid(&h,101));
 for(unsigned i=0;i<6;i++){h.cal[i][0]=3900;h.cal[i][1]=200;h.cal[i][2]=2050;}
 assert(tx15_snapshot_valid(&h,100));
 h.cal[0][2]=4000;assert(!tx15_snapshot_valid(&h,100));
 h.cal[0][2]=2050;h.mode=0;assert(!tx15_snapshot_valid(&h,100));
 h.mode=4;assert(tx15_snapshot_valid(&h,100));h.version=2;assert(!tx15_snapshot_valid(&h,100));
}
""")
   r=subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror','-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),'-I',str(ROOT/'hardware/tx15/board'),str(p/'test.c'),'-o',str(p/'test.exe')],env=env,capture_output=True,text=True,encoding="utf8",errors="replace")
   self.assertEqual(r.returncode,0,r.stderr);subprocess.run([str(p/'test.exe')],env=env,check=True)

 def test_calibration_only_changes_and_failed_save_remain_dirty(self):
  gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
  env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ['PATH'])
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.c').write_text(r"""
#include <assert.h>
#include <string.h>
#include "common.h"
#include "config/model.h"
#include "config/tx.h"
#include "hardware/tx15/board/settings_snapshot.h"
struct Transmitter Transmitter;
static unsigned calls;static int success=1;
u32 Crc(const void *p,u32 n) {const unsigned char *b=p;u32 v=0;while(n--)v=v*31+*b++;return v;}
int tx15_settings_save(unsigned model,const void *data,unsigned bytes) {
 assert(model==1);assert(bytes>=sizeof(Model)+sizeof(struct tx15_snapshot_header));
 const struct tx15_snapshot_header *h=data;assert(tx15_snapshot_valid(h,sizeof(Model)));
 assert(h->mode==(unsigned)Transmitter.mode);assert(h->cal[1][1]==Transmitter.calibration[1].min);
 calls++;return success;
}
void tx15_rf_model_reset(void) {}
int main(void) {
 memset(&Model,0,sizeof(Model));memset(&Transmitter,0,sizeof(Transmitter));Transmitter.current_model=1;Transmitter.mode=2;
 assert(CONFIG_IsModelChanged());assert(CONFIG_SaveModelIfNeeded());assert(calls==1 && !CONFIG_IsModelChanged());
 Transmitter.calibration[1].max=3900;Transmitter.calibration[1].min=200;Transmitter.calibration[1].zero=2048;
 assert(CONFIG_IsModelChanged());success=0;assert(!CONFIG_SaveModelIfNeeded());assert(CONFIG_IsModelChanged());
 success=1;assert(CONFIG_SaveModelIfNeeded());assert(!CONFIG_IsModelChanged());
 Transmitter.mode=1;assert(CONFIG_IsModelChanged());assert(CONFIG_SaveModelIfNeeded());assert(!CONFIG_IsModelChanged());
}
""")
   inc=[]
   for x in ('','src','src/target/tx/radiomaster/tx15','src/target/drivers/filesystems','src/gui/320x240x16','src/pages/320x240x16'):inc+=['-I',str(ROOT/x)]
   r=subprocess.run([str(gcc),'-std=c99','-O1','-ffunction-sections','-fdata-sections','-fno-asynchronous-unwind-tables','-DTX15_PERSISTENCE=1','-DTX15_ELRS_RC=1','-DUSE_OWN_PRINTF=0','-I',str(ROOT.parent/'tools/msys64/ucrt64/lib/gcc/x86_64-w64-mingw32/16.2.0/include'),'-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),*inc,str(p/'test.c'),str(ROOT/'src/config/model.c'),'-Wl,--gc-sections,--exclude-all-symbols','-o',str(p/'test.exe')],env=env,capture_output=True,text=True,encoding="utf8",errors="replace")
   self.assertEqual(r.returncode,0,r.stderr);subprocess.run([str(p/'test.exe')],env=env,check=True)
