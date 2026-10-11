"""Native switch catalog and persisted source migration regressions."""
import os, subprocess, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]

class SwitchUpgradeTests(unittest.TestCase):
    def run_c(self, code, sources):
        gcc = Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env = dict(os.environ, PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp)/'test.c'; exe=Path(tmp)/'test.exe'; c.write_text(code)
            inc=[]
            for p in ('','src','src/target/tx/radiomaster/tx15','src/target/drivers/filesystems',
                      'src/gui/320x240x16','src/pages/320x240x16'):
                inc += ['-I', str(ROOT/p)]
            r=subprocess.run([str(gcc),'-std=c11','-Os','-fshort-enums','-ffunction-sections','-fdata-sections','-fno-asynchronous-unwind-tables',
                '-DUSE_OWN_PRINTF=0','-I',str(ROOT.parent/'tools/msys64/ucrt64/lib/gcc/x86_64-w64-mingw32/16.2.0/include'),
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),*inc,
                str(c),*[str(ROOT/p) for p in sources],'-Wl,--gc-sections,--exclude-all-symbols','-o',str(exe)],
                env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_native_menu_and_mixer_see_three_positions_for_every_switch(self):
        self.run_c(r'''
#include <assert.h>
#include "common.h"
#include "config/tx.h"
#include "mixer.h"
#include "hardware/tx15/board/controls.h"
struct Transmitter Transmitter;struct tx15_controls tx15_controls;
volatile uint16_t tx15_analog_raw[6];volatile uint32_t tx15_analog_status;
int main(void) {
 unsigned first[]={INP_SWA0,INP_SWB0,INP_SWC0,INP_SWD0,INP_SWE0,INP_SWF0};
 unsigned hi[]={13,11,9,7,15,4},lo[]={12,10,8,6,14,5};
 for(unsigned i=0;i<6;i++) {
  assert(INPUT_NumSwitchPos(first[i])==3);
  for(unsigned p=0;p<3;p++) {
   unsigned raw=p==1?0xffff:0xffff^(1u<<(p==0?lo[i]:hi[i]));
   tx15_controls_reset(&tx15_controls);
   tx15_controls_decode(&tx15_controls,0xffff,raw,0);
   tx15_controls_decode(&tx15_controls,0xffff,raw,20);
   for(unsigned j=0;j<3;j++) assert(CHAN_ReadInput(first[i]+j)==(j==p?10000:-10000));
   assert(INPUT_GetFirstSwitch(first[i]+p)==(int)first[i]);
  }
 }
 return 0;
}''', ['src/inputs.c','src/target/tx/radiomaster/tx15/analog.c','hardware/tx15/board/control_decode.c'])

    def test_frozen_v1_layout_matches_the_original_native_catalog(self):
        self.run_c(r'''
#define TX15_LEGACY_INPUT_LAYOUT 1
#include <assert.h>
#include <stddef.h>
#include "common.h"
#include "config/model.h"
#include "target/tx/radiomaster/tx15/model_migrate.h"
int main(void) {
 assert(NUM_TX_INPUTS==28);
 assert(sizeof(struct Model)==sizeof(struct tx15_model_v1));
 assert(sizeof(struct tx15_model_v1)==3400);
 assert(offsetof(struct Model,safety)==offsetof(struct tx15_model_v1,safety));
 assert(offsetof(struct Model,mixers)==offsetof(struct tx15_model_v1,mixers));
 assert(offsetof(struct Model,trims)==offsetof(struct tx15_model_v1,trims));
 assert(offsetof(struct Model,pagecfg2)==offsetof(struct tx15_model_v1,pagecfg2));
 return 0;
}''', [])

    def test_legacy_model_and_calibration_can_be_loaded_without_changing_flash(self):
        migration=ROOT/'src/target/tx/radiomaster/tx15/model_migrate.h'
        self.assertTrue(migration.exists(), 'Legacy source migration is missing')
        self.run_c(r'''
#include <assert.h>
#include <string.h>
#include "common.h"
#include "config/model.h"
#include "config/tx.h"
#include "target/tx/radiomaster/tx15/model_migrate.h"
static unsigned reads,stored_bytes;static unsigned char stored[20000];
static int read_store(unsigned id,void *out,unsigned bytes) {
 assert(id==1);reads++;if(bytes!=stored_bytes)return 0;memcpy(out,stored,bytes);return 1;
}
int main(void) {
 struct tx15_model_v1 old={0};struct Model next;
 strcpy(old.name,"Saved aircraft");old.fixed_id=12345;old.tx15_modules[0].enabled=1;
 old.mixers[0].src=29;old.mixers[0].sw=0x80|22;old.mixers[0].scalar=60;
 old.mixers[1].src=19;old.mixers[1].sw=20;
 old.trims[0].src=3;old.trims[0].sw=21;old.trims[0].value[0]=15;
 old.limits[0].safetysw=28;old.limits[0].safetyval=-100;
 old.timer[0].src=23;old.timer[0].resetsrc=0x80|29;
 old.train_sw=22;old.swashmix[0]=60;old.swashmix[1]=100;old.swashmix[2]=50;old.safety[29]=SAFE_MIN;
 ELEM_SET_X(old.pagecfg2.elem[0],10);ELEM_SET_TYPE(old.pagecfg2.elem[0],ELEM_TOGGLE);
 old.pagecfg2.elem[0].src=21;
 ELEM_SET_X(old.pagecfg2.elem[1],10);ELEM_SET_TYPE(old.pagecfg2.elem[1],ELEM_BAR);
 old.pagecfg2.elem[1].src=1;
 tx15_model_from_v1(&next,&old);
 assert(!strcmp(next.name,old.name) && next.fixed_id==12345 && next.tx15_modules[0].enabled);
 assert(next.mixers[0].src==31 && next.mixers[0].sw==(0x80|INP_SWF2));
 assert(next.mixers[0].scalar==60 && next.mixers[1].src==INP_SWE1 && next.mixers[1].sw==INP_SWE2);
 assert(next.trims[0].src==3 && next.trims[0].sw==INP_SWF1 && next.trims[0].value[0]==15);
 assert(next.limits[0].safetysw==INP_SW65 && next.limits[0].safetyval==-100);
 assert(next.timer[0].src==INP_SW60 && next.timer[0].resetsrc==(0x80|31));
 assert(next.train_sw==INP_SWF2 && !memcmp(next.swashmix,old.swashmix,3) && next.safety[31]==SAFE_MIN);
 assert(next.safety[INP_SWE0]==0 && next.safety[INP_SWF0]==0);
 assert(next.pagecfg2.elem[0].src==INP_SWF1 && next.pagecfg2.elem[1].src==1);
 for(unsigned i=0;i<=28+NUM_CHANNELS+MAX_PPM_IN_CHANNELS;i++) {
  unsigned want=i<=18?i:i<=20?i+1:i<=22?i+2:i+2;
  assert(tx15_source_from_v1(i)==want);
  assert(tx15_source_from_v1(i|128)==(want|128));
 }
 struct {struct tx15_snapshot_header header;struct tx15_model_v1 model;} saved={0};
 struct Transmitter tx={0};saved.model=old;
 saved.header.magic=TX15_SNAPSHOT_MAGIC;saved.header.version=1;
 saved.header.model_bytes=sizeof(old);saved.header.mode=3;
 for(unsigned i=0;i<6;i++){saved.header.cal[i][0]=3900;saved.header.cal[i][1]=200;saved.header.cal[i][2]=2048;}
 stored_bytes=sizeof(saved);memcpy(stored,&saved,stored_bytes);
 memset(&next,0,sizeof(next));assert(tx15_model_restore(&next,&tx,1,read_store));
 assert(tx.mode==3 && next.mixers[0].src==31 && tx.calibration[5].zero==2048);
 struct {struct tx15_snapshot_header header;struct Model model;} saved2={0};
 saved2.header=saved.header;saved2.header.version=2;saved2.header.model_bytes=sizeof(next);saved2.model=next;
 stored_bytes=sizeof(saved2);memcpy(stored,&saved2,stored_bytes);
 memset(&next,0,sizeof(next));assert(tx15_model_restore(&next,&tx,1,read_store));
 assert(next.mixers[0].src==31); /* Must not migrate current IDs twice. */
 saved2.header.version=3;memcpy(stored,&saved2,stored_bytes);
 assert(!tx15_model_restore(&next,&tx,1,read_store));
 saved2.header.version=2;saved2.header.cal[0][2]=4000;memcpy(stored,&saved2,stored_bytes);
 assert(!tx15_model_restore(&next,&tx,1,read_store));
 assert(reads);
 return 0;
}''', [])
