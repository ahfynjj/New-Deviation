"""S1/S2 capture filter and real Mix edit lifecycle, without a simulator."""
import unittest
import test_switch_upgrade as switches

class SourceCaptureTests(unittest.TestCase):
    run_c = switches.SwitchUpgradeTests.run_c

    def test_movement_noise_ambiguity_and_rearm(self):
        self.run_c(r'''
#include <assert.h>
#include "knob_capture.h"
int main(void) {
 struct tx15_knob_capture c={0};int v[2]={-9000,8000};
 assert(!tx15_knob_capture_step(&c,v,1,1)); /* Existing position is not movement. */
 v[0]+=999;assert(!tx15_knob_capture_step(&c,v,1,1));
 v[0]++;assert(tx15_knob_capture_step(&c,v,1,1)==1);
 assert(!tx15_knob_capture_step(&c,v,1,1));
 v[1]-=1000;assert(tx15_knob_capture_step(&c,v,1,1)==2);
 v[0]+=1000;v[1]-=1000;assert(!tx15_knob_capture_step(&c,v,1,1));
 assert(!tx15_knob_capture_step(&c,v,1,1)); /* Ambiguous motion consumed. */
 assert(!tx15_knob_capture_step(&c,v,0,1));
 v[0]=9999;assert(!tx15_knob_capture_step(&c,v,1,1));
 v[0]-=1000;assert(tx15_knob_capture_step(&c,v,1,1)==1);
 assert(!tx15_knob_capture_step(&c,v,1,0));
 v[1]=0;assert(!tx15_knob_capture_step(&c,v,1,1));
 v[1]=-1000;assert(tx15_knob_capture_step(&c,v,1,1)==2);
 return 0;
}''', ['src/target/tx/radiomaster/tx15/knob_capture.c'])

    def test_source_fields_capture_only_knobs_while_editing(self):
        self.run_c(r'''
#include <assert.h>
#include "common.h"
#define ENABLE_GUIOBJECT
#include "gui/gui.h"
#include "pages.h"
#include "config/tx.h"
#include "mix_switch.h"
struct Transmitter Transmitter;struct tx15_controls tx15_controls;
volatile u32 tx15_analog_status=4;
static guiObject_t *selected;static int page=PAGEID_MIXTEMPL;
static u32 now,keys;static int knobs[2];static u8 value=INP_AILERON|128;
static unsigned updates;static int last_value;
s32 CHAN_ReadInput(int ch){return ch==INP_S1?knobs[0]:ch==INP_S2?knobs[1]:9000;}
guiObject_t *GUI_GetSelected(void){return selected;}
guiObject_t *GUI_IsModal(void){return NULL;}
int PAGE_GetID(void){return page;}
void _GUI_Redraw(guiObject_t *o){(void)o;}
u32 CLOCK_getms(void){return now;}u32 ScanButtons(void){return keys;}
void AUTODIMMER_Check(void){}
const char *input(guiObject_t *o,int src,int v,void *d){(void)o;*(u8*)d=INPUT_SelectInput(*(u8*)d,src,NULL);updates++;last_value=v;return "";}
void inverse(guiObject_t *o,void *d){(void)o;*(u8*)d^=128;}
const char *manual(guiObject_t *o,int dir,void *d){(void)o;*(u8*)d=INPUT_SelectSource(*(u8*)d,dir,NULL);return "";}
static void key(u32 k){now+=100;keys=k;BUTTON_Handler();tx15_mix_switch_poll();}
static void tap(u32 k){key(k);key(0);}
int main(void){
 guiTextSelect_t src={0},sw={0};src.header.Type=TextSelect;src.header.flags=1;
 src.enable=1;src.InputValueCB=input;src.ValueCB=manual;src.SelectCB=inverse;src.cb_data=&value;
 sw=src;tx15_mix_source_register(&src);tx15_mix_switch_register(&sw);
 selected=(guiObject_t*)&src;tx15_controls.valid=63;
 tx15_mix_switch_init();knobs[0]=5000;tx15_mix_switch_poll();assert(!updates);
 tap(CHAN_ButtonMask(BUT_ENTER));assert(src.enable&TX15_SWITCH_EDITING);assert(!updates);
 knobs[0]+=100;tx15_mix_switch_poll();assert(!updates);
 tx15_controls.position[0]=2;tx15_mix_switch_poll();assert(!updates);
 knobs[0]+=900;tx15_mix_switch_poll();assert(value==(INP_S1|128) && updates==1 && last_value==6000);
 knobs[1]=-1000;tx15_mix_switch_poll();assert(value==(INP_S2|128) && updates==2 && last_value==-1000);
 tap(CHAN_ButtonMask(BUT_ENTER));knobs[0]=-8000;tx15_mix_switch_poll();assert(updates==2);
 tap(CHAN_ButtonMask(BUT_ENTER));assert(updates==2); /* Fresh baseline. */
 Transmitter.ignore_src=1u<<INP_S1;knobs[0]+=1000;tx15_mix_switch_poll();assert(updates==2);
 Transmitter.ignore_src=0;tx15_analog_status=0;knobs[0]=0;tx15_mix_switch_poll();
 tx15_analog_status=4;tx15_mix_switch_poll();assert(updates==2);
 knobs[0]=1000;tx15_mix_switch_poll();assert(value==(INP_S1|128) && updates==3);
 tap(CHAN_ButtonMask(BUT_EXIT));assert(!(src.enable&TX15_SWITCH_EDITING));
 tap(CHAN_ButtonMask(BUT_ENTER));selected=(guiObject_t*)&sw;tx15_mix_switch_poll();
 assert(!(src.enable&TX15_SWITCH_EDITING));tap(CHAN_ButtonMask(BUT_ENTER));
 knobs[1]=8000;tx15_mix_switch_poll();assert(updates==3); /* Switch role ignores knobs. */
 tx15_controls.position[0]=1;tx15_mix_switch_poll();assert(value==(INP_SWA1|128) && updates==4);
 selected=(guiObject_t*)&src;tx15_mix_switch_poll();tap(CHAN_ButtonMask(BUT_ENTER));
 tap(CHAN_ButtonMask(BUT_DOWN));assert(value==(INP_SWA2|128)); /* Manual selection retained. */
 key(CHAN_ButtonMask(BUT_ENTER));now+=510;BUTTON_Handler();key(0);
 assert(value==INP_SWA2 && (src.enable&TX15_SWITCH_EDITING));
 tx15_mix_switch_forget(selected);assert(!(src.enable&TX15_SWITCH_EDITING));
 knobs[0]=-9000;tx15_mix_switch_poll();assert(updates==4);
 return 0;
}''', ['src/target/tx/radiomaster/tx15/mix_switch.c',
       'src/target/tx/radiomaster/tx15/switch_capture.c',
       'src/target/tx/radiomaster/tx15/knob_capture.c',
       'src/buttons.c','src/inputs.c','src/gui/textsel.c'])
