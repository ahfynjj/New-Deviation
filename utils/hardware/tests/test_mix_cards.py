import unittest
import test_switch_upgrade as helper

class MixCardsTests(unittest.TestCase):
    run_c=helper.SwitchUpgradeTests.run_c
    def test_dense_geometry_more_page_and_touch_callbacks(self):
        self.run_c(r'''
#include <assert.h>
#define TX15_CARD_UI 1
#include "common.h"
#include "pages.h"
#include "config/model.h"
#include "card_ui.h"
#include "mix_switch.h"
static struct mixer_page memory,*mp=&memory;
static struct advmixcfg_obj objects,*gui=&objects;
static struct advmixcfg_obj_g3 *gui3=&objects.u.g3;
static struct advmixcfg_obj_g1 *gui1=&objects.u.g1;
static unsigned fields,labels,graphs,sources,values,touches,saves,changes;
static guiObject_t *selected;
char tempstring[TEMPSTRINGLENGTH];
int PAGE_GetID(void){return PAGEID_MIXTEMPL;}
guiObject_t *GUI_GetSelected(void){return selected;}
void GUI_SetSelected(guiObject_t *o){selected=o;}
struct LabelDesc tx15_card_font(unsigned n){(void)n;return (struct LabelDesc){0};}
static const char *v(guiObject_t *o,int d,void *p){(void)o;(void)d;(void)p;return "x";}
#define templatetype_cb v
#define set_nummixers_cb v
#define set_mixernum_cb v
#define set_source_cb v
#define set_drsource_cb v
#define set_mux_cb v
#define set_number100_cb v
#define set_curvename_cb v
static void sel(guiObject_t *o,void *p){(void)o;(void)p;}
#define sourceselect_cb sel
#define curveselect_cb sel
#define reorder_cb sel
static const char *iv(guiObject_t *o,int s,int v,void *p){(void)o;(void)s;(void)v;(void)p;return "";}
#define set_input_switch_cb iv
#define set_input_source_cb iv
static const char *show_trim_cb(guiObject_t *o,const void *p){(void)o;(void)p;return "Trim";}
static void toggle_trim_cb(guiObject_t *o,const void *p){(void)o;(void)p;}
static void okcancel_cb(guiObject_t *o,const void *p){(void)o;saves+=(uintptr_t)p;}
static s32 eval_mixer_cb(s32 x,void *p){(void)p;return x;}
static s32 eval_chan_cb(void *p){(void)p;return 0;}
static u8 curpos_cb(s16 *x,s16 *y,u8 p,void *d){(void)x;(void)y;(void)p;(void)d;return 0;}
static u8 touch_cb(s16 x,s16 y,void *p){(void)x;(void)y;(void)p;return 0;}
void MIXPAGE_ChangeTemplate(int h){(void)h;changes++;}
unsigned MIXER_SourceHasTrim(unsigned src){(void)src;return 1;}
static void box(guiObject_t *o,unsigned x,unsigned y,unsigned w,unsigned h){
 assert(w && h && x+w<=480 && y+h<=320);o->box=(struct guiBox){x,y,w,h};o->flags=1;
}
guiObject_t *GUI_CreateLabelBox(guiLabel_t *o,u16 x,u16 y,u16 w,u16 h,const struct LabelDesc *d,
 const char *(*cb)(guiObject_t *,const void *),void (*p)(guiObject_t *,s8,const void *),const void *data){
 (void)d;labels++;box((guiObject_t *)o,x,y,w,h);o->strCallback=cb;o->pressCallback=p;o->cb_data=data;return (guiObject_t *)o;
}
guiObject_t *GUI_CreateTextSelectPlate(guiTextSelect_t *o,u16 x,u16 y,u16 w,u16 h,const struct LabelDesc *d,
 void (*s)(guiObject_t *,void *),const char *(*v)(guiObject_t *,int,void *),void *p){
 (void)d;assert(h>=40);fields++;box((guiObject_t *)o,x,y,w,h);o->header.Type=TextSelect;o->ValueCB=v;o->SelectCB=s;o->cb_data=p;return (guiObject_t *)o;
}
guiObject_t *GUI_CreateTextSourcePlate(guiTextSelect_t *o,u16 x,u16 y,u16 w,u16 h,const struct LabelDesc *d,
 void (*s)(guiObject_t *,void *),const char *(*v)(guiObject_t *,int,void *),
 const char *(*i)(guiObject_t *,int,int,void *),void *p){
 o->InputValueCB=i;return GUI_CreateTextSelectPlate(o,x,y,w,h,d,s,v,p);
}
guiObject_t *GUI_CreateXYGraph(guiXYGraph_t *o,u16 x,u16 y,u16 w,u16 h,s16 a,s16 b,s16 c,s16 d,u16 e,u16 f,
 s32 (*v)(s32,void *),u8 (*p)(s16 *,s16 *,u8,void *),u8 (*t)(s16,s16,void *),void *data){
 (void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)v;(void)p;(void)t;(void)data;
 graphs++;box((guiObject_t *)o,x,y,w,h);return (guiObject_t *)o;
}
guiObject_t *GUI_CreateBarGraph(guiBarGraph_t *o,u16 x,u16 y,u16 w,u16 h,s16 a,s16 b,u8 dir,s32 (*v)(void *),void *p){
 (void)a;(void)b;(void)dir;(void)v;(void)p;box((guiObject_t *)o,x,y,w,h);return (guiObject_t *)o;
}
void GUI_SetHidden(guiObject_t *o,u8 hide){if(hide)o->flags|=2;else o->flags&=~2;}
void GUI_RemoveHierObjects(guiObject_t *o){(void)o;}
void _GUI_Redraw(guiObject_t *o){(void)o;}
void tx15_mix_source_register(guiTextSelect_t *o){(void)o;sources++;}
void tx15_mix_switch_register(guiTextSelect_t *o){(void)o;sources++;}
void tx15_mix_value_register(guiTextSelect_t *o){(void)o;values++;}
void tx15_mix_field_touch(guiObject_t *o){selected=o;touches++;}
void tx15_mix_field_step(guiObject_t *o,int d){(void)o;(void)d;}
void tx15_mix_switch_forget(guiObject_t *o){(void)o;}
void tx15_card_mix_rows_reset(void){}
void tx15_card_mix_row(guiTextSelect_t *o,const char *s){(void)o;(void)s;}
#include "src/pages/320x240x16/advanced/mixer_cards.inc"
int main(void){
 mp->cur_template=MIXERTEMPLATE_COMPLEX;mp->cur_mixer=&mp->mixer[0];mp->num_mixers=2;
 mp->mixer[0].src=INP_AILERON;
 tx15_mix_card_more=0;tx15_mix_complex_cards(0);
 assert(fields==8 && sources==2 && graphs==1 && values==6);
 assert(PAGE_MixCardActive());assert(PAGE_MixCardHit(12,44)==0);
 assert(PAGE_MixCardHit(303,259)==4 && PAGE_MixCardHit(12,84)==-1);
 PAGE_MixCardTap(30,55);assert(touches==1 && selected==(guiObject_t *)&gui3->src);
 assert(OBJ_IS_HIDDEN((guiObject_t *)&gui3->nummix));
 tx15_mix_card_more_cb(NULL,-1,NULL);
 assert(tx15_mix_card_more && !OBJ_IS_HIDDEN((guiObject_t *)&gui3->nummix));
 assert(OBJ_IS_HIDDEN((guiObject_t *)&gui3->src));
 PAGE_MixCardTap(30,55);assert(touches==2 && selected==(guiObject_t *)&gui3->nummix);
 assert(PAGE_MixCardHit(30,235)==-1);
 PAGE_MixCardTap(400,300);assert(saves==1);
 mp->cur_template=MIXERTEMPLATE_EXPO_DR;assert(!PAGE_MixCardActive());
 return 0;
}''',[])
