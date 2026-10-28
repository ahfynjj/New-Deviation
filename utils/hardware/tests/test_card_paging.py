"""Real scrollable implementation + real menu enumeration and linked rows."""
import unittest
import test_switch_upgrade as helper

class CardPagingTests(unittest.TestCase):
    run_c=helper.SwitchUpgradeTests.run_c
    def test_all_seven_main_items_rotary_next_and_page_hint(self):
        self.run_c(r'''
#include <assert.h>
#include <string.h>
#define TX15_MENU_TOUCH 1
#define TX15_CARD_UI 1
#define TX15_TOUCH_DIAGNOSTIC 1
#define TX15_ELRS_RC 1
#define TX15_AUDIO 1
#define TX15_STORAGE 1
#include "common.h"
#define ENABLE_GUIOBJECT
#include "pages.h"
#include "config/display.h"
#include "card_ui.h"
struct Model Model;struct display_settings Display;
struct _gui_objs gui_objs;struct pagemem pagemem;char tempstring[TEMPSTRINGLENGTH];
guiObject_t *objHEAD,*objSELECTED;u8 FullRedraw;
const struct ImageMap image_map[IMAGE_MAP_END]={{0,16,16,0,0}};
static unsigned pushed;
void connect_object(guiObject_t *o){guiObject_t **p=&objHEAD;while(*p)p=&(*p)->next;*p=o;o->next=NULL;OBJ_SET_USED(o,1);}
void GUI_RemoveAllObjects(void){while(objHEAD){guiObject_t *o=objHEAD;objHEAD=o->next;if(objSELECTED==o)objSELECTED=NULL;o->flags=0;}FullRedraw=1;}
void GUI_SetSelected(guiObject_t *o){objSELECTED=o;}
void GUI_SetHidden(guiObject_t *o,u8 h){OBJ_SET_HIDDEN(o,h);}
void GUI_SetScrollbar(guiScrollbar_t *s,u8 p){s->cur_pos=p;}
guiObject_t *GUI_CreateScrollbar(guiScrollbar_t *o,u16 x,u16 y,u16 h,u8 count,guiObject_t *parent,
 int (*cb)(guiObject_t *,u8,s8,void *),void *data){
 (void)x;(void)y;(void)h;(void)count;(void)parent;(void)cb;(void)data;
 memset(o,0,sizeof(*o));o->header.Type=Scrollbar;connect_object((guiObject_t *)o);return (guiObject_t *)o;
}
guiObject_t *GUI_CreateLabelBox(guiLabel_t *o,u16 x,u16 y,u16 w,u16 h,const struct LabelDesc *d,
 const char *(*text)(guiObject_t *,const void *),void (*cb)(guiObject_t *,s8,const void *),const void *data){
 memset(o,0,sizeof(*o));o->header.Type=Label;o->header.box=(struct guiBox){x,y,w,h};o->desc=*d;
 o->strCallback=text;o->pressCallback=cb;o->cb_data=data;OBJ_SET_SELECTABLE((guiObject_t *)o,cb!=NULL);
 connect_object((guiObject_t *)o);return (guiObject_t *)o;
}
u8 PAGE_SetModal(u8 m){return m;}
void PAGE_ShowHeader(const char *s){(void)s;}
const char *PAGE_GetName(int n){(void)n;return "Menu";}
void PAGE_SetScrollable(guiScrollable_t *o,u16 *p){(void)o;(void)p;}
void PAGE_Pop(void){}
void PAGE_PushByID(enum PageID id,int n){(void)n;pushed=id;}
struct LabelDesc tx15_card_font(unsigned n){(void)n;return (struct LabelDesc){0};}
#include "src/gui/scrollable.c"
#include "src/pages/320x240x16/menus.c"
int main(void){
 Model.mixer_mode=1;PAGE_MenuInit(0);
 const unsigned expected[]={PAGEID_MODELMNU,PAGEID_TXMENU,PAGEID_USB,PAGEID_ELRSLUA,
  PAGEID_AUDIOTEST,PAGEID_TOUCHTEST,PAGEID_STORAGETEST};
 assert(tx15_menu_items==7 && gui->scrollable.item_count==3);
 guiObject_t *o=GUI_ScrollableGetNextSelectable(&gui->scrollable,NULL);
 for(unsigned i=0;i<7;i++){
  assert(o && (uintptr_t)((guiLabel_t *)o)->cb_data==expected[i]);
  if(i<6)o=GUI_ScrollableGetNextSelectable(&gui->scrollable,o);
 }
 PAGE_MenuTouchScroll(-1);assert(PAGE_MenuTouchRow()==0);
 PAGE_MenuTouchScroll(1);assert(PAGE_MenuTouchRow()==2);
 PAGE_MenuTouchTap(40,80);assert(pushed==PAGEID_STORAGETEST);
 PAGE_MenuTouchScroll(-1);
 assert(menu_footer[2].strCallback); /* Page count must be visible. */
 assert(strstr(menu_footer[2].strCallback(NULL,menu_footer[2].cb_data),"1/2"));
 PAGE_MenuTouchScroll(1);
 assert(strstr(menu_footer[2].strCallback(NULL,menu_footer[2].cb_data),"2/2"));
 return 0;
}''',[])
