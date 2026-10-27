"""Native menu-only touch: actual router and geometry, no simulator."""
import unittest
import test_switch_upgrade as switches

class MenuTouchTests(unittest.TestCase):
    run_c = switches.SwitchUpgradeTests.run_c

    def test_native_menu_layout_and_callback_route(self):
        self.run_c(r'''
#include <assert.h>
#include <string.h>
#define TX15_MENU_TOUCH 1
#define TX15_TOUCH_DIAGNOSTIC 1
#define TX15_ELRS_RC 1
#define TX15_AUDIO 1
#define TX15_STORAGE 1
#include "common.h"
#include "pages.h"
#include "gui/gui.h"
#include "config/model.h"
#include "config/display.h"
#include "menu_touch.h"
struct Model Model;struct display_settings Display;
struct _gui_objs gui_objs;struct pagemem pagemem;
char tempstring[TEMPSTRINGLENGTH];
static unsigned labels,footer,first,visible=6,items,pushed,popped;
static int pushed_id;
u8 PAGE_SetModal(u8 value){return value;}
void PAGE_ShowHeader(const char *s){assert(s);}
const char *PAGE_GetName(int id){(void)id;return "Menu";}
void PAGE_SetScrollable(guiScrollable_t *s,u16 *p){(void)s;(void)p;}
void PAGE_PushByID(enum PageID id,int arg){(void)arg;pushed++;pushed_id=id;}
void PAGE_Pop(void){popped++;}
guiObject_t *GUI_CreateScrollable(guiScrollable_t *s,u16 x,u16 y,u16 w,u16 h,u16 rh,u8 count,
 int (*cb)(int,int,int,void *),guiObject_t *(*get)(int,int,void *),int (*size)(int,void *),void *data){
 (void)get;(void)size;(void)data;
 assert(!x && y==36 && w==480 && h==240 && rh==40);items=count;s->item_count=count;
 for(unsigned i=0;i<6 && i<count;i++)cb(i,i,y+i*rh,0);
 return (guiObject_t *)s;
}
guiObject_t *GUI_CreateLabelBox(guiLabel_t *o,u16 x,u16 y,u16 w,u16 h,const struct LabelDesc *desc,
 const char *(*text)(guiObject_t *,const void *),void (*cb)(guiObject_t *,s8,const void *),const void *data){
 (void)desc;(void)text;(void)data;
 assert(h==40 && x+w<=480 && y+h<=320);
 if(y==280){assert(!cb && w==144);footer++;}else labels++;
 return (guiObject_t *)o;
}
int GUI_ScrollableCurrentRow(guiScrollable_t *s){(void)s;return first;}
int GUI_ScrollableVisibleRows(guiScrollable_t *s){(void)s;return visible;}
guiObject_t *GUI_ShowScrollableRowOffset(guiScrollable_t *s,int offset){(void)s;first=offset>>8;return 0;}
void GUI_SetSelected(guiObject_t *o){(void)o;}
#include "src/pages/320x240x16/menus.c"
int main(void){
 Model.mixer_mode=1;
 PAGE_MenuInit(0);assert(labels && footer==3 && items>6);
 PAGE_MenuTouchTap(40,80);assert(pushed==1);
 int expected=pushed_id;PAGE_MenuTouchTap(40,35);assert(pushed==1);
 PAGE_MenuTouchScroll(1);assert(first==(items-6<6?items-6:6));
 PAGE_MenuTouchScroll(-1);assert(first==0);
 PAGE_MenuTouchTap(40,80);assert(pushed==2 && pushed_id==expected);
 PAGE_MenuTouchTap(8,280);assert(popped==1);
 first=items-1;PAGE_MenuTouchTap(40,80);assert(pushed==2);
 return 0;
}''', [])

    def test_router_release_swipe_cancellation_and_ownership(self):
        self.run_c(r'''
#include <assert.h>
#define TX15_MENU_TOUCH 1
#define TX15_TOUCH_DIAGNOSTIC 1
#include "common.h"
#include "pages.h"
#include "menu_touch.h"
#include "hardware/tx15/board/touch.h"
struct tx15_touch_report tx15_touch_report;
static unsigned ms,started,stopped,mapped,taps,scrolls,release_guards;
static int page=PAGEID_MENU,row,scroll_direction,modal;
static struct tx15_touch_event queued;static int pending;
u32 CLOCK_getms(void){return ms;}
int PAGE_GetID(void){return page;}
guiObject_t *GUI_IsModal(void){return modal?(guiObject_t *)&queued:NULL;}
int PAGE_MenuTouchRow(void){return row;}
void PAGE_MenuTouchTap(unsigned x,unsigned y){assert(x==40 && y==80);taps++;}
void PAGE_MenuTouchScroll(int direction){scrolls++;scroll_direction=direction;}
void tx15_touch_start(uint32_t n){(void)n;started++;tx15_touch_report.state=TX15_TOUCH_PROBING;}
void tx15_touch_stop(uint32_t n){(void)n;stopped++;tx15_touch_report.state=TX15_TOUCH_OFF;}
void tx15_touch_set_map(unsigned flags,uint32_t n){(void)n;assert(!flags);mapped++;}
void tx15_touch_require_release(uint32_t n){(void)n;release_guards++;}
int tx15_touch_take(struct tx15_touch_event *e){if(!pending)return 0;*e=queued;pending=0;return 1;}
static void event(unsigned kind,unsigned x,unsigned y,unsigned when){
 ms=when;queued=(struct tx15_touch_event){when,x,y,kind};pending=1;tx15_menu_touch_poll();
}
#include "src/target/tx/radiomaster/tx15/menu_touch.c"
int main(void){
 tx15_menu_touch_poll();assert(started==1 && release_guards==1);
 tx15_touch_report.state=TX15_TOUCH_READY;tx15_menu_touch_poll();assert(mapped==1);
 event(TX15_TOUCH_DOWN,40,80,20);event(TX15_TOUCH_UP,40,80,50);assert(!taps);
 event(TX15_TOUCH_DOWN,40,80,120);assert(!taps);
 event(TX15_TOUCH_UP,40,80,160);assert(taps==1);
 event(TX15_TOUCH_UP,40,80,170);assert(taps==1);
 event(TX15_TOUCH_DOWN,40,80,200);event(TX15_TOUCH_MOVE,40,40,220);
 event(TX15_TOUCH_UP,40,40,240);assert(scrolls==1 && scroll_direction==1 && taps==1);
 event(TX15_TOUCH_DOWN,40,80,300);event(TX15_TOUCH_MOVE,80,80,310);
 event(TX15_TOUCH_UP,40,80,330);assert(taps==1); /* returning to origin is not a tap */
 event(TX15_TOUCH_DOWN,40,75,400);event(TX15_TOUCH_UP,40,80,420);assert(taps==1); /* row boundary */
 event(TX15_TOUCH_DOWN,40,80,500);row++;
 event(TX15_TOUCH_UP,40,80,520);assert(taps==1);
 event(TX15_TOUCH_DOWN,40,80,600);event(TX15_TOUCH_CANCEL,40,80,610);
 event(TX15_TOUCH_UP,40,80,620);assert(taps==1);
 event(TX15_TOUCH_DOWN,40,80,700);tx15_touch_report.state=TX15_TOUCH_ERROR;
 event(TX15_TOUCH_UP,40,80,720);assert(taps==1);
 tx15_menu_touch_suspend();assert(stopped==1);
 page=PAGEID_TOUCHTEST;tx15_touch_report.state=TX15_TOUCH_READY;pending=1;
 tx15_menu_touch_poll();assert(pending && started==1 && stopped==1);
 page=PAGEID_MIXER;pending=0;tx15_menu_touch_poll();assert(started==1);
 page=PAGEID_MENU;ms=1000;tx15_menu_touch_poll();assert(started==2);
 tx15_touch_report.state=TX15_TOUCH_READY;
 event(TX15_TOUCH_DOWN,40,80,1200);page=PAGEID_TXMENU;
 event(TX15_TOUCH_UP,40,80,1220);assert(taps==1);
 modal=1;tx15_menu_touch_poll();assert(!owned && !active);
 return 0;
}''', [])

    def test_layout_hit_contract(self):
        self.run_c(r'''
#include <assert.h>
#include "menu_touch.h"
int main(void){
 assert(tx15_menu_touch_hit(0,36)==0);
 assert(tx15_menu_touch_hit(479,275)==5);
 assert(tx15_menu_touch_hit(40,35)==-1 && tx15_menu_touch_hit(40,276)==-1);
 assert(tx15_menu_touch_hit(8,280)==6 && tx15_menu_touch_hit(151,319)==6);
 assert(tx15_menu_touch_hit(152,280)==-1 && tx15_menu_touch_hit(168,280)==7);
 assert(tx15_menu_touch_hit(328,319)==8 && tx15_menu_touch_hit(472,319)==-1);
 assert(tx15_menu_touch_hit(480,100)==-1 && tx15_menu_touch_hit(0,320)==-1);
 return 0;
}''', [])
