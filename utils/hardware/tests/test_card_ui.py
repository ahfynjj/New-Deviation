"""Native card hit contract. Product code stays separate from visual PNGs."""
import unittest
import test_switch_upgrade as helper
import test_menu_touch
import test_switch_capture

class CardUITests(unittest.TestCase):
    run_c=helper.SwitchUpgradeTests.run_c
    def test_mix_router_cancels_rebuild_swipe_and_legacy_template(self):
        self.run_c(r'''
#include <assert.h>
#define TX15_CARD_UI 1
#define TX15_MENU_TOUCH 1
#define TX15_TOUCH_DIAGNOSTIC 1
#include "common.h"
#include "pages.h"
#include "card_ui.h"
#include "menu_touch.h"
#include "hardware/tx15/board/touch.h"
struct tx15_touch_report tx15_touch_report;
static unsigned ms,taps,stops;static int enabled=1,generation,pending;
static struct tx15_touch_event queued;
u32 CLOCK_getms(void){return ms;}
int PAGE_GetID(void){return PAGEID_MIXTEMPL;}
guiObject_t *GUI_IsModal(void){return NULL;}
int PAGE_MixCardActive(void){return enabled;}
int PAGE_MixCardGeneration(void){return generation;}
int PAGE_MixCardHit(unsigned x,unsigned y){return x<300 && y>=44 && y<84?0:-1;}
void PAGE_MixCardTap(unsigned x,unsigned y){assert(PAGE_MixCardHit(x,y)==0);taps++;}
int PAGE_MenuTouchRow(void){assert(0);return 0;}
void PAGE_MenuTouchTap(unsigned x,unsigned y){(void)x;(void)y;assert(0);}
void PAGE_MenuTouchScroll(int d){(void)d;assert(0);}
void tx15_touch_start(uint32_t n){(void)n;tx15_touch_report.state=TX15_TOUCH_PROBING;}
void tx15_touch_stop(uint32_t n){(void)n;stops++;tx15_touch_report.state=TX15_TOUCH_OFF;}
void tx15_touch_require_release(uint32_t n){(void)n;}
void tx15_touch_set_map(unsigned f,uint32_t n){(void)n;assert(!f);}
int tx15_touch_take(struct tx15_touch_event *e){if(!pending)return 0;*e=queued;pending=0;return 1;}
static void event(unsigned kind,unsigned y,unsigned now){ms=now;queued=(struct tx15_touch_event){now,40,y,kind};pending=1;tx15_menu_touch_poll();}
#include "src/target/tx/radiomaster/tx15/menu_touch.c"
int main(void){
 tx15_menu_touch_poll();tx15_touch_report.state=TX15_TOUCH_READY;
 event(TX15_TOUCH_DOWN,60,120);assert(!taps);
 event(TX15_TOUCH_UP,60,160);assert(taps==1);
 event(TX15_TOUCH_DOWN,60,200);generation++;
 event(TX15_TOUCH_UP,60,220);assert(taps==1);
 event(TX15_TOUCH_DOWN,60,300);event(TX15_TOUCH_MOVE,100,320);
 event(TX15_TOUCH_UP,60,340);assert(taps==1);
 event(TX15_TOUCH_DOWN,60,400);enabled=0;
 event(TX15_TOUCH_UP,60,420);assert(taps==1 && stops==1);
 return 0;
}''',[])
    def test_numeric_edit_touch_and_physical_exit(self):
        class Adapted(test_switch_capture.SwitchCaptureTests):
            def run_c(case,code,sources):
                code=code.replace('int PAGE_GetID(void){return page;}',
                    'int PAGE_GetID(void){return page;}\nvoid GUI_SetSelected(guiObject_t *o){selected=o;}')
                code=code.replace('assert(redraws>0);return 0;',r'''
 page=PAGEID_MIXTEMPL;selected=(guiObject_t *)&field;
 field.enable=1;field.InputValueCB=NULL;field.SelectCB=NULL;
 tx15_mix_value_register(&field);before=updates;
 tx15_mix_field_touch(selected);assert(field.enable&TX15_SWITCH_EDITING);
 tx15_controls.position[0]=0;tx15_mix_switch_poll();assert(updates==before);
 u8 old=field_value;tap(CHAN_ButtonMask(BUT_DOWN));assert(field_value!=old);
 tx15_mix_field_touch(selected);assert(!(field.enable&TX15_SWITCH_EDITING));
 tx15_mix_field_touch(selected);tap(CHAN_ButtonMask(BUT_EXIT));
 assert(!(field.enable&TX15_SWITCH_EDITING) && page_exits==1);
 assert(redraws>0);return 0;
''')
                return helper.SwitchUpgradeTests.run_c(case,code,sources)
        Adapted('test_real_button_flow_arms_confirms_cancels_and_preserves_manual_inversion').test_real_button_flow_arms_confirms_cancels_and_preserves_manual_inversion()

    def test_actual_plate_draw_and_scoped_palette_restore(self):
        self.run_c(r'''
#include <assert.h>
#include <string.h>
#define TX15_CARD_UI 1
#include "common.h"
#include "pages.h"
#include "config/display.h"
#include "card_ui.h"
struct display_settings Display;
static unsigned font,prints,clears;
guiObject_t *GUI_GetSelected(void){return NULL;}
u8 LCD_SetFont(unsigned f){font=f;return f;}
void LCD_SetFontColor(u16 c){(void)c;}
void LCD_GetStringDimensions(const u8 *s,u16 *w,u16 *h){*w=strlen((const char *)s)*(font==2?11:7);*h=font==2?23:15;}
void LCD_PrintStringXY(unsigned x,unsigned y,const char *s){u16 w,h;LCD_GetStringDimensions((const u8 *)s,&w,&h);assert(x+w<=480 && y+h<=320);prints++;}
void LCD_FillRect(u16 x,u16 y,u16 w,u16 h,u16 c){(void)c;assert(x+w<=480 && y+h<=320);clears++;}
void LCD_DrawRoundRect(u16 x,u16 y,u16 w,u16 h,u16 r,u16 c){(void)r;(void)c;assert(x+w<=480 && y+h<=320);}
void LCD_FillRoundRect(u16 x,u16 y,u16 w,u16 h,u16 r,u16 c){LCD_DrawRoundRect(x,y,w,h,r,c);}
void LCD_DrawLine(u16 x,u16 y,u16 a,u16 b,u16 c){(void)c;assert(x<480 && y<320 && a<480 && b<320);}
void LCD_DrawRect(u16 x,u16 y,u16 w,u16 h,u16 c){(void)c;assert(x+w<=480 && y+h<=320);}
void LCD_DrawFastVLine(int16_t x,int16_t y,int16_t h,u16 c){(void)c;assert(x>=0 && y>=0 && x<480 && y+h<=320);}
void LCD_DrawFastHLine(u16 x,u16 y,u16 w,u16 c){(void)c;assert(x+w<=480 && y<320);}
void GUI_DrawImageHelper(u16 x,u16 y,const struct ImageMap *map,u8 i){(void)x;(void)y;(void)map;(void)i;assert(0 && "plate must not use a bitmap");}
static const char *value(guiObject_t *o,int d,void *p){(void)o;(void)d;(void)p;return "100%";}
#include "src/target/tx/radiomaster/tx15/card_ui.c"
#include "src/gui/textsel.c"
int main(void){
 Display.font[20].font=2;Display.font[9].font=1;
 Display.background.bg_color=123;Display.select_color=456;
 struct display_settings original=Display;
 tx15_card_page_theme(PAGEID_MENU);assert(Display.background.bg_color==TX15_CARD_BG);
 tx15_card_page_theme(PAGEID_MIXTEMPL);assert(Display.select_color==TX15_CARD_ACCENT);
 guiTextSelect_t field={0};field.type=TEXTSELECT_TEXT;field.header.Type=TextSelect;
 field.header.box=(struct guiBox){108,44,196,40};field.desc=tx15_card_font(1);field.ValueCB=value;
 GUI_DrawTextSelect((guiObject_t *)&field);assert(prints==1 && clears>=1);
 guiLabel_t label={0};label.header.box=(struct guiBox){322,156,146,96};label.desc=tx15_card_font(1);
 tx15_card_draw_label(&label,"Transmitter menu");assert(prints==2);
 tx15_card_page_theme(PAGEID_EDITCURVE);assert(!memcmp(&original,&Display,sizeof(Display)));
 return 0;
}''',[])
    def test_actual_card_menu_enumeration_and_scroll(self):
        class Adapted(test_menu_touch.MenuTouchTests):
            def run_c(case,code,sources):
                code=code.replace('#define TX15_MENU_TOUCH 1','#define TX15_MENU_TOUCH 1\n#define TX15_CARD_UI 1')
                code=code.replace('visible=6','visible=2').replace('y==36 && w==480 && h==240 && rh==40','y==52 && w==480 && h==208 && rh==104')
                code=code.replace('i<6 && i<count','i<2 && i<count')
                code=code.replace('assert(h==40 && x+w<=480 && y+h<=320);','assert((h==40 || h==96) && x+w<=480 && y+h<=320);')
                code=code.replace('items>6','items>2').replace('first==(items-6<6?items-6:6)','first==2').replace('first=items-1','first=items')
                code=code.replace('#include "src/pages/320x240x16/menus.c"','struct LabelDesc tx15_card_font(unsigned n){(void)n;return (struct LabelDesc){0};}\n#include "src/pages/320x240x16/menus.c"')
                return helper.SwitchUpgradeTests.run_c(case,code,sources)
        case=Adapted('test_native_menu_layout_and_callback_route')
        case.test_native_menu_layout_and_callback_route()
    def test_card_hit_targets_and_gaps(self):
        self.run_c(r'''
#include <assert.h>
#define TX15_CARD_UI 1
#include "menu_touch.h"
int main(void){
 assert(tx15_menu_touch_hit(12,52)==0);
 assert(tx15_menu_touch_hit(157,147)==0);
 assert(tx15_menu_touch_hit(158,90)==-1);
 assert(tx15_menu_touch_hit(167,52)==1);
 assert(tx15_menu_touch_hit(322,156)==5);
 assert(tx15_menu_touch_hit(467,251)==5);
 assert(tx15_menu_touch_hit(12,148)==-1);
 assert(tx15_menu_touch_hit(0,40)==-1);
 assert(tx15_menu_touch_hit(8,280)==6);
 assert(tx15_menu_touch_hit(168,280)==7);
 assert(tx15_menu_touch_hit(328,319)==8);
 return 0;
}''',[])
