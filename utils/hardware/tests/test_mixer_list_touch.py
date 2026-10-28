import unittest
import test_switch_upgrade as helper

class MixerListTouchTests(unittest.TestCase):
    run_c=helper.SwitchUpgradeTests.run_c
    def test_list_geometry_channel_mapping_and_actions(self):
        self.run_c(r'''
#include <assert.h>
#include <string.h>
#define TX15_CARD_UI 1
#include "common.h"
#include "pages.h"
#include "config/model.h"
#include "card_ui.h"
struct Model Model;char tempstring[TEMPSTRINGLENGTH];
static struct advmixer_obj widgets,*gui=&widgets;
static u16 current_selected;
static unsigned first,edit_ch,limit_ch,virt_ch,monitors,orders,pops;
static struct Mixer mixers[NUM_MIXERS];
struct LabelDesc tx15_card_font(unsigned n){(void)n;return (struct LabelDesc){0};}
struct Mixer *MIXER_GetAllMixers(void){return mixers;}
enum TemplateType MIXER_GetTemplate(int ch){(void)ch;return MIXERTEMPLATE_SIMPLE;}
const char *MIXER_TemplateName(enum TemplateType t){(void)t;return "Simple";}
const char *INPUT_SourceName(char *s,unsigned src){(void)src;strcpy(s,"AIL");return s;}
static int _is_virt_cyclic(int ch){(void)ch;return 0;}
const char *MIXPAGE_ChanNameProtoCB(guiObject_t *o,const void *p){(void)o;(void)p;return "CH";}
static void limitselect_cb(guiObject_t *o,const void *p){(void)o;limit_ch=(uintptr_t)p+1;}
static void virtname_cb(guiObject_t *o,const void *p){(void)o;virt_ch=(uintptr_t)p+1;}
static void templateselect_cb(guiObject_t *o,const void *p){(void)o;edit_ch=(uintptr_t)p+1;}
static void show_chantest_cb(guiObject_t *o,const void *p){(void)o;(void)p;monitors++;}
static void reorder_cb(guiObject_t *o,const void *p){(void)o;(void)p;orders++;}
void PAGE_Pop(void){pops++;}
void PAGE_ShowHeader(const char *s){assert(s);}
void PAGE_SetScrollable(guiScrollable_t *o,u16 *p){(void)o;(void)p;}
guiObject_t *GUI_CreateLabelBox(guiLabel_t *o,u16 x,u16 y,u16 w,u16 h,const struct LabelDesc *d,
 const char *(*t)(guiObject_t *,const void *),void (*cb)(guiObject_t *,s8,const void *),const void *p){
 (void)d;assert(w>=40 && h>=40 && x+w<=480 && y+h<=320);
 o->header.box=(struct guiBox){x,y,w,h};o->cb_data=p;o->strCallback=t;o->pressCallback=cb;
 return (guiObject_t *)o;
}
guiObject_t *GUI_CreateScrollable(guiScrollable_t *o,u16 x,u16 y,u16 w,u16 h,u16 rh,u8 n,
 int (*r)(int,int,int,void *),guiObject_t *(*g)(int,int,void *),int (*s)(int,void *),void *p){
 (void)g;(void)s;(void)p;assert(x==0 && y==44 && w==480 && h==220 && rh==44);
 o->item_count=n;for(unsigned i=0;i<5;i++)r(i,i,44+i*44,NULL);return (guiObject_t *)o;
}
int GUI_ScrollableCurrentRow(guiScrollable_t *o){(void)o;return first;}
guiObject_t *GUI_ShowScrollableRowOffset(guiScrollable_t *o,int n){(void)o;first=n>>8;return NULL;}
void GUI_SetSelected(guiObject_t *o){(void)o;}
#include "src/pages/320x240x16/advanced/mixer_list_cards.inc"
int main(void){
 Model.num_channels=6;tx15_mixer_list_title();tx15_mixer_list_page();
 assert(gui->scrollable.item_count==6+NUM_VIRT_CHANNELS);
 PAGE_MixerTouchTap(30,55);assert(limit_ch==1);
 PAGE_MixerTouchTap(150,55);assert(edit_ch==1);
 assert(PAGE_MixerTouchHit(104,55)==-1 && PAGE_MixerTouchHit(30,86)==-1);
 PAGE_MixerTouchScroll(1);assert(first==5);
 PAGE_MixerTouchTap(150,99);assert(edit_ch==NUM_OUT_CHANNELS+1);
 PAGE_MixerTouchTap(30,99);assert(virt_ch==NUM_OUT_CHANNELS+1);
 PAGE_MixerTouchTap(280,20);PAGE_MixerTouchTap(400,20);assert(monitors==1 && orders==1);
 PAGE_MixerTouchTap(30,300);assert(pops==1);
 return 0;
}''',[])
