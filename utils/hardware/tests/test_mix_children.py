"""Native child-page construction plus actual curve/limit callbacks."""
import unittest
import test_switch_upgrade as helper

BASE=r'''
#include <assert.h>
#include <string.h>
#define TX15_CARD_UI 1
#define TX15_RAM_APPLICATION 1
#include "common.h"
#include "pages.h"
#include "config/model.h"
#include "card_ui.h"
#include "mix_switch.h"
struct _gui_objs gui_objs;struct pagemem pagemem;
char tempstring[TEMPSTRINGLENGTH];u8 FullRedraw;
static guiObject_t *selected;static unsigned popped,registered;
guiObject_t *GUI_GetSelected(void){return selected;}
void GUI_SetSelected(guiObject_t *o){selected=o;}
void _GUI_Redraw(guiObject_t *o){(void)o;}
void PAGE_Pop(void){popped++;}
void tx15_mix_touch_begin(int p){(void)p;registered=0;}
void tx15_mix_touch_add(guiObject_t *o){(void)o;registered++;}
void tx15_mix_touch_changed(void){}
void tx15_mix_switch_forget(guiObject_t *o){(void)o;}
void tx15_mix_value_register(guiTextSelect_t *o){o->enable|=TX15_VALUE_FIELD;}
void tx15_mix_switch_register(guiTextSelect_t *o){o->enable|=TX15_SWITCH_FIELD;}
void tx15_card_mix_row(guiTextSelect_t *o,const char *s){(void)s;o->desc.style=LABEL_MIX_ROW;}
struct LabelDesc tx15_card_font(unsigned n){(void)n;return (struct LabelDesc){.style=LABEL_PANEL};}
static void bounds(guiObject_t *o,unsigned x,unsigned y,unsigned w,unsigned h){assert(w && h && x+w<=480 && y+h<=320);o->box=(struct guiBox){x,y,w,h};o->flags=1;}
guiObject_t *GUI_CreateLabelBox(guiLabel_t *o,u16 x,u16 y,u16 w,u16 h,const struct LabelDesc *f,
const char *(*v)(guiObject_t *,const void *),void (*cb)(guiObject_t *,s8,const void *),const void *p){
 bounds((guiObject_t *)o,x,y,w,h);o->header.Type=Label;o->desc=*f;o->strCallback=v;o->pressCallback=cb;o->cb_data=p;return (guiObject_t *)o;
}
guiObject_t *GUI_CreateTextSelectPlate(guiTextSelect_t *o,u16 x,u16 y,u16 w,u16 h,const struct LabelDesc *f,
void (*cb)(guiObject_t *,void *),const char *(*v)(guiObject_t *,int,void *),void *p){
 bounds((guiObject_t *)o,x,y,w,h);o->header.Type=TextSelect;o->desc=*f;o->enable=1;o->SelectCB=cb;o->ValueCB=v;o->cb_data=p;return (guiObject_t *)o;
}
guiObject_t *GUI_CreateTextSourcePlate(guiTextSelect_t *o,u16 x,u16 y,u16 w,u16 h,const struct LabelDesc *f,
void (*cb)(guiObject_t *,void *),const char *(*v)(guiObject_t *,int,void *),const char *(*iv)(guiObject_t *,int,int,void *),void *p){
 GUI_CreateTextSelectPlate(o,x,y,w,h,f,cb,v,p);o->InputValueCB=iv;return (guiObject_t *)o;
}
guiObject_t *GUI_CreateXYGraph(guiXYGraph_t *o,u16 x,u16 y,u16 w,u16 h,s16 a,s16 b,s16 c,s16 d,u16 e,u16 f,
s32 (*v)(s32,void *),u8 (*pt)(s16 *,s16 *,u8,void *),u8 (*touch)(s16,s16,void *),void *p){
 bounds((guiObject_t *)o,x,y,w,h);o->header.Type=XYGraph;o->min_x=a;o->min_y=b;o->max_x=c;o->max_y=d;o->grid_x=e;o->grid_y=f;
 o->CallBack=v;o->point_cb=pt;o->touch_cb=touch;o->cb_data=p;return (guiObject_t *)o;
}
void GUI_SetHidden(guiObject_t *o,u8 hide){if(hide)o->flags|=2;else o->flags&=~2;}
void GUI_TextSelectEnable(guiTextSelect_t *o,u8 en){o->enable=(o->enable&~1)|(!!en);}
u8 GUI_IsTextSelectEnabled(guiObject_t *o){return ((guiTextSelect_t *)o)->enable&1;}
void GUI_TextSelectEnablePress(guiTextSelect_t *o,u8 e){(void)o;(void)e;}
s32 GUI_TextSelectHelper(s32 v,s32 min,s32 max,s8 d,u32 s,u32 l,u8 *changed){
 (void)l;s32 old=v;v+=d*(s32)s;if(v<min)v=min;if(v>max)v=max;if(changed)*changed=v!=old;return v;
}
'''

class MixChildrenTests(unittest.TestCase):
    run_c=helper.SwitchUpgradeTests.run_c
    def test_reorder_factory_move_save_and_cancel(self):
        self.run_c(BASE+r'''
static int first,applied,cleaned;static u8 saved;
int GUI_ScrollableCurrentRow(guiScrollable_t *o){(void)o;return first;}
guiObject_t *GUI_ShowScrollableRowOffset(guiScrollable_t *o,int pos){(void)o;first=pos>>8;return NULL;}
guiObject_t *GUI_ShowScrollableRowCol(guiScrollable_t *o,int row,int col){(void)o;(void)col;first=row;return NULL;}
guiObject_t *GUI_CreateScrollable(guiScrollable_t *o,u16 x,u16 y,u16 w,u16 h,u16 rh,u8 n,
int (*row)(int,int,int,void *),guiObject_t *(*get)(int,int,void *),int (*size)(int,void *),void *p){
 (void)get;(void)size;bounds((guiObject_t *)o,x,y,w,h);o->item_count=n;
 for(unsigned i=0;i<n && i<5;i++)row(i,i,y+i*rh,p);return (guiObject_t *)o;
}
static const char *order_text(u8 index){(void)index;return "CH1";}
static void order_return(u8 *list){if(list){applied++;saved=list[0];}else cleaned++;}
#include "src/pages/320x240x16/reorder_list.c"
int main(void){
 u8 list[4]={0};rl.list=list;rl.count=rl.max=3;rl.selected=0;rl.text_cb=order_text;rl.return_page=order_return;
 PAGE_ReorderInit(0);assert(gui->value.header.box.width==292 && gui->name[0].header.box.height==40);
 tx15_order_select(NULL,-1,(void *)1);tx15_order_action(NULL,-1,(void *)MOVE_UP);
 assert(rl.selected==0 && list[0]==2 && list[1]==1);
 tx15_order_action(NULL,-1,(void *)SAVE);assert(applied==1 && cleaned==1 && saved==2 && popped==1);
 tx15_order_action(NULL,-1,(void *)6);assert(applied==1 && cleaned==2 && popped==2);
 return 0;
}''',[])

    def test_curve_factory_tap_reverse_and_cancel_save(self):
        self.run_c(BASE+r'''
const char *PAGEMIXER_SetNumberCB(guiObject_t *o,int d,void *p){(void)o;*(s8 *)p+=d;return "";}
#include "src/pages/320x240x16/advanced/mixer_curves.c"
int main(void){
 struct Curve original={0};CURVE_SET_TYPE(&original,CURVE_3POINT);
 original.points[0]=-100;original.points[1]=0;original.points[2]=100;
 pagemem.u.mixer_page.cur_mixer=&pagemem.u.mixer_page.mixer[0];
 edit->curveptr=&original;PAGE_EditCurvesInit(0);
 assert(gui->value.header.box.height==40 && registered==1);
 assert(!OBJ_IS_HIDDEN((guiObject_t *)&gui->smooth));
 gui->graph.touch_cb(CHAN_MAX_VALUE,CHAN_MIN_VALUE,gui->graph.cb_data);
 assert(edit->pointnum==2 && edit->curve.points[2]==-100 && original.points[2]==100);
 tx15_curve_action(NULL,-1,NULL);assert(original.points[2]==100 && popped==1);
 edit->reverse=1;gui->graph.touch_cb(CHAN_MAX_VALUE,CHAN_MAX_VALUE,NULL);
 assert(edit->pointnum==0 && edit->curve.points[0]==100);
 tx15_curve_action(NULL,-1,(void *)1);assert(original.points[0]==100 && original.points[2]==-100 && popped==2);
 return 0;
}''',['src/curves.c'])

    def test_limits_two_banks_safety_revert_and_live_back(self):
        self.run_c(BASE+r'''
static struct Limit limit;
struct Limit *MIXER_GetLimit(int ch){(void)ch;return &limit;}
const char *MIXPAGE_ChanNameProtoCB(guiObject_t *o,const void *p){(void)o;(void)p;return "CH1";}
const char *INPUT_SourceName(char *s,unsigned src){(void)src;strcpy(s,"SA0");return s;}
int INPUT_SelectSource(int src,int dir,u8 *changed){*changed=dir!=0;return src+dir;}
int INPUT_SelectInput(int src,int new,u8 *changed){*changed=src!=new;return new;}
#include "src/pages/320x240x16/advanced/mixer_limits.c"
int main(void){
 limit.max=100;PAGE_EditLimitsInit(0);
 assert(gui->safeval.header.box.height==40 && !(gui->safeval.enable&1));
 assert(OBJ_IS_HIDDEN((guiObject_t *)&gui->subtrim));
 tx15_limit_action(NULL,-1,(void *)1);assert(tx15_limit_bank==1);
 assert(!OBJ_IS_HIDDEN((guiObject_t *)&gui->subtrim));
 assert(OBJ_IS_HIDDEN((guiObject_t *)&gui->reverse));
 gui->max.ValueCB((guiObject_t *)&gui->max,1,gui->max.cb_data);assert(limit.max==101);
 tx15_limit_action(NULL,-1,(void *)2);assert(limit.max==100);
 tx15_limit_action(NULL,-1,(void *)3);assert(limit.flags&CH_FAILSAFE_EN);
 gui->safety.InputValueCB((guiObject_t *)&gui->safety,INP_SWA1,0,gui->safety.cb_data);
 assert(gui->safeval.enable&1);
 tx15_limit_action(NULL,-1,NULL);assert(popped==1 && limit.safetysw==INP_SWA1);
 return 0;
}''',[])
