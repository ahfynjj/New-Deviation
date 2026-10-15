"""Native mixer switch capture: transitions, edit lifecycle and real buttons."""
import unittest
import test_switch_upgrade as switches

class SwitchCaptureTests(unittest.TestCase):
    run_c=switches.SwitchUpgradeTests.run_c

    def test_edit_indicator_is_drawn_after_the_real_selection_highlight(self):
        self.run_c(r'''
#include <assert.h>
#include "common.h"
#define ENABLE_GUIOBJECT
#include "gui/gui.h"
#include "config/display.h"
#include "mix_switch.h"
struct display_settings Display;
static unsigned last_color,rects;
void LCD_DrawRect(u16 x,u16 y,u16 w,u16 h,u16 color){(void)x;(void)y;(void)w;(void)h;last_color=color;rects++;}
#define DRAW(name) void name(guiObject_t *obj){(void)obj;}
DRAW(GUI_DrawButton) DRAW(GUI_DrawLabel) DRAW(GUI_DrawImage) DRAW(GUI_DrawDialog)
DRAW(GUI_DrawXYGraph) DRAW(GUI_DrawBarGraph) DRAW(GUI_DrawKeyboard) DRAW(GUI_DrawScrollbar)
DRAW(GUI_DrawScrollable) DRAW(GUI_DrawRect) DRAW(GUI_DrawTextSelect)
int GUI_TouchButton(guiObject_t *o,int p){(void)o;(void)p;return 0;}
u8 GUI_TouchImage(guiObject_t *o,struct touch *t,s8 p){(void)o;(void)t;(void)p;return 0;}
u8 GUI_TouchLabel(guiObject_t *o,struct touch *t,s8 p){(void)o;(void)t;(void)p;return 0;}
u8 GUI_TouchTextSelect(guiObject_t *o,struct touch *t,s8 p){(void)o;(void)t;(void)p;return 0;}
u8 GUI_TouchKeyboard(guiObject_t *o,struct touch *t,s8 p){(void)o;(void)t;(void)p;return 0;}
u8 GUI_TouchXYGraph(guiObject_t *o,struct touch *t,u8 p){(void)o;(void)t;(void)p;return 0;}
extern guiObject_t *objSELECTED;
int main(void){
 guiTextSelect_t field={0};field.header.Type=TextSelect;field.header.box.width=96;field.header.box.height=24;
 field.enable=1|TX15_SWITCH_FIELD;objSELECTED=(guiObject_t*)&field;
 Display.select_width=2;Display.select_color=0x07ff;
 GUI_DrawObject(objSELECTED);assert(rects==2 && last_color==0x07ff);
 field.enable|=TX15_SWITCH_EDITING;GUI_DrawObject(objSELECTED);
 assert(last_color==0xfdc0); /* Armed orange must survive the cyan focus border. */
 field.enable&=~TX15_SWITCH_EDITING;GUI_DrawObject(objSELECTED);assert(last_color==0x07ff);
 return 0;
}''',['src/gui/gui.c'])

    def test_real_button_flow_arms_confirms_cancels_and_preserves_manual_inversion(self):
        self.run_c(r'''
#include <assert.h>
#include <string.h>
#include "common.h"
#define ENABLE_GUIOBJECT
#include "gui/gui.h"
#include "pages.h"
#include "config/tx.h"
#include "mix_switch.h"
struct Transmitter Transmitter;struct tx15_controls tx15_controls;
volatile u32 tx15_analog_status=4;
s32 CHAN_ReadInput(int ch){(void)ch;return 0;}
static guiObject_t *selected;static int page=PAGEID_MIXTEMPL;static unsigned updates,redraws;
static u32 now,keys;static u8 field_value=INP_NONE;static unsigned page_exits,page_saves;
guiObject_t *GUI_GetSelected(void){return selected;}
guiObject_t *GUI_IsModal(void){return NULL;}
int PAGE_GetID(void){return page;}
void _GUI_Redraw(guiObject_t *obj){(void)obj;redraws++;}
u32 CLOCK_getms(void){return now;}u32 ScanButtons(void){return keys;}
void AUTODIMMER_Check(void){}
const char *input(guiObject_t *o,int src,int value,void *data){(void)o;assert(value==CHAN_MAX_VALUE);*(u8*)data=INPUT_SelectInput(*(u8*)data,src,NULL);updates++;return "";}
const char *manual(guiObject_t *o,int dir,void *data){(void)o;*(u8*)data=INPUT_SelectSource(*(u8*)data,dir,NULL);return "";}
void inverse(guiObject_t *o,void *data){(void)o;*(u8*)data^=128;}
static void key(u32 mask){now+=100;keys=mask;BUTTON_Handler();tx15_mix_switch_poll();}
static void tap(u32 mask){key(mask);key(0);}
static unsigned page_buttons(u32 keys,unsigned flags,void *data){
 (void)data;
 if(CHAN_ButtonIsPressed(keys,BUT_EXIT)) {if(flags&(BUTTON_RELEASE|BUTTON_LONGPRESS))page_exits++;return 1;}
 if(CHAN_ButtonIsPressed(keys,BUT_ENTER) && (flags&BUTTON_LONGPRESS)){page_saves++;return 1;}
 return 0;
}
int main(void){
 guiTextSelect_t field={0},source={0};field.header.Type=TextSelect;
 field.header.flags=1;field.enable=1;field.InputValueCB=input;field.ValueCB=manual;
 field.SelectCB=inverse;field.cb_data=&field_value;
 source=field;tx15_mix_switch_register(&field);selected=(guiObject_t*)&field;
 tx15_controls.valid=63;for(unsigned i=0;i<6;i++)tx15_controls.position[i]=1;
 buttonAction_t page_action={0};
 BUTTON_RegisterCallback(&page_action,CHAN_ButtonMask(BUT_EXIT)|CHAN_ButtonMask(BUT_ENTER),
  BUTTON_PRESS|BUTTON_RELEASE|BUTTON_LONGPRESS|BUTTON_PRIORITY,page_buttons,NULL);
 tx15_mix_switch_init();tx15_mix_switch_poll();assert(updates==0);
 tap(CHAN_ButtonMask(BUT_ENTER));assert(field.enable&TX15_SWITCH_EDITING);
 assert(field_value==INP_NONE && updates==0);
 tx15_controls.position[0]=2;tx15_mix_switch_poll();assert(field_value==INP_SWA2 && updates==1);
 tx15_mix_switch_poll();assert(updates==1);
 tap(CHAN_ButtonMask(BUT_DOWN));assert(field_value==INP_SWB0); /* Manual wheel increment. */
 key(CHAN_ButtonMask(BUT_ENTER));now+=510;BUTTON_Handler();now+=110;BUTTON_Handler();key(0);
 assert(field_value==(INP_SWB0|128) && (field.enable&TX15_SWITCH_EDITING));
 assert(page_saves==0);
 tx15_controls.position[1]=0;tx15_mix_switch_poll();assert(field_value==(INP_SWB0|128));
 tap(CHAN_ButtonMask(BUT_ENTER));assert(!(field.enable&TX15_SWITCH_EDITING));
 tx15_controls.position[1]=2;tx15_mix_switch_poll();assert(field_value==(INP_SWB0|128));
 tap(CHAN_ButtonMask(BUT_ENTER));assert(field_value==(INP_SWB0|128));
 tx15_controls.position[2]=0;tx15_mix_switch_poll();assert(field_value==(INP_SWC0|128));
 key(CHAN_ButtonMask(BUT_EXIT));now+=510;BUTTON_Handler();key(0);
 assert(!(field.enable&TX15_SWITCH_EDITING) && page_exits==0);
 unsigned before=updates;tx15_controls.position[2]=1;tx15_mix_switch_poll();assert(updates==before);
 /* Ordinary source fields cannot arm switch capture. */
 selected=(guiObject_t*)&source;tap(CHAN_ButtonMask(BUT_ENTER));
 tx15_controls.position[3]=2;tx15_mix_switch_poll();assert(updates==before);
 selected=(guiObject_t*)&field;tap(CHAN_ButtonMask(BUT_ENTER));
 Transmitter.ignore_src=1u<<INP_SWD0;tx15_controls.position[3]=0;tx15_mix_switch_poll();assert(updates==before);
 Transmitter.ignore_src=0;
 /* Losing focus or removing/recreating a field discards the armed state. */
 selected=NULL;tx15_mix_switch_poll();assert(!(field.enable&TX15_SWITCH_EDITING));
 selected=(guiObject_t*)&field;tap(CHAN_ButtonMask(BUT_ENTER));
 tx15_mix_switch_forget(selected);assert(!(field.enable&TX15_SWITCH_EDITING));
 tx15_controls.position[4]=2;tx15_mix_switch_poll();assert(updates==before);
 tap(CHAN_ButtonMask(BUT_ENTER));page=PAGEID_MENU;tx15_mix_switch_poll();
 assert(!(field.enable&TX15_SWITCH_EDITING));
 tap(CHAN_ButtonMask(BUT_EXIT));assert(page_exits==1);
 assert(redraws>0);return 0;
}''',['src/target/tx/radiomaster/tx15/mix_switch.c','src/target/tx/radiomaster/tx15/switch_capture.c',
       'src/target/tx/radiomaster/tx15/knob_capture.c',
       'src/buttons.c','src/inputs.c','src/gui/textsel.c'])

    def test_only_new_unambiguous_valid_switch_transitions_are_captured(self):
        self.run_c(r'''
#include <assert.h>
#include "switch_capture.h"
int main(void) {
 struct tx15_switch_capture c={0};struct tx15_controls controls={0};
 controls.valid=63;for(unsigned i=0;i<6;i++)controls.position[i]=1;
 assert(!tx15_switch_capture_step(&c,&controls,0));
 assert(!tx15_switch_capture_step(&c,&controls,1));
 assert(!tx15_switch_capture_step(&c,&controls,1));
 for(unsigned i=0;i<6;i++)for(unsigned p=0;p<3;p++) {
  controls.position[i]=p;
  assert(tx15_switch_capture_step(&c,&controls,1)==(int)(i*3+p+1));
  assert(!tx15_switch_capture_step(&c,&controls,1));
 }
 controls.position[0]=1;controls.position[1]=1;
 assert(!tx15_switch_capture_step(&c,&controls,1)); /* Ambiguous, consume both. */
 assert(!tx15_switch_capture_step(&c,&controls,1));
 controls.valid=0;assert(!tx15_switch_capture_step(&c,&controls,1));
 controls.position[0]=2;controls.valid=63;
 assert(!tx15_switch_capture_step(&c,&controls,1)); /* Recovery is a baseline. */
 controls.position[0]=0;assert(tx15_switch_capture_step(&c,&controls,1)==1);
 assert(!tx15_switch_capture_step(&c,&controls,0));
 controls.position[0]=2;assert(!tx15_switch_capture_step(&c,&controls,1));
 controls.position[0]=255;assert(!tx15_switch_capture_step(&c,&controls,1));
 controls.position[0]=0;assert(!tx15_switch_capture_step(&c,&controls,1));
 controls.position[0]=1;assert(tx15_switch_capture_step(&c,&controls,1)==2);
 return 0;
}''',['src/target/tx/radiomaster/tx15/switch_capture.c'])
