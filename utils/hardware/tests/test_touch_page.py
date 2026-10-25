"""Independent 480x320 touch diagnostic geometry and lifecycle."""
import unittest
import test_switch_upgrade as switches
class TouchPageTests(unittest.TestCase):
    run_c=switches.SwitchUpgradeTests.run_c
    def test_actual_page_actions_geometry_idle_redraw_and_cancel(self):
        self.run_c(r'''
#include <assert.h>
#include <string.h>
#define TX15_TOUCH_DIAGNOSTIC 1
#include "common.h"
#include "gui/gui.h"
#include "config/display.h"
#include "hardware/tx15/board/touch.h"
struct display_settings Display;struct tx15_touch_report tx15_touch_report;
static unsigned ms,started,stopped,mapped,status_count,actions,redraws,canvas_draws;
static void (*callbacks[3])(guiObject_t *,s8,const void *);
static const void *arguments[3];
static void (*draw_canvas)(guiObject_t *,const void *);
u32 CLOCK_getms(void){return ms;}
u8 PAGE_SetModal(u8 modal){return modal;}
void PAGE_ShowHeader(const char *s){assert(strstr(s,"TOU1"));}
void tx15_touch_start(uint32_t now){(void)now;started++;tx15_touch_report.state=TX15_TOUCH_PROBING;}
void tx15_touch_stop(uint32_t now){(void)now;stopped++;tx15_touch_report.state=TX15_TOUCH_OFF;}
void tx15_touch_cycle_map(uint32_t now){(void)now;mapped++;tx15_touch_report.map_flags++;}
int tx15_touch_take(struct tx15_touch_event *e){(void)e;return 0;}
void _GUI_Redraw(guiObject_t *o){(void)o;redraws++;}
guiObject_t *GUI_CreateLabelBox(guiLabel_t *o,u16 x,u16 y,u16 w,u16 h,const struct LabelDesc *desc,
 const char *(*text)(guiObject_t *,const void *),void (*cb)(guiObject_t *,s8,const void *),const void *data){
 (void)desc;assert(w && h && x+w<=480 && y+h<=320 && text);
 assert(text((guiObject_t *)o,data));
 if(cb){assert(actions<3);callbacks[actions]=cb;arguments[actions++]=data;}
 else status_count++;
 return (guiObject_t *)o;
}
guiObject_t *GUI_CreateRectCB(guiRect_t *o,u16 x,u16 y,u16 w,u16 h,const struct LabelDesc *desc,
 void (*cb)(guiObject_t *,const void *),const void *data){
 (void)desc;(void)data;assert(x+w<=480 && y+h<=280);draw_canvas=cb;return (guiObject_t *)o;
}
void LCD_DrawRect(u16 x,u16 y,u16 w,u16 h,u16 c){(void)c;assert(x+w<=480 && y+h<=320);canvas_draws++;}
void LCD_DrawFastHLine(u16 x,u16 y,u16 w,u16 c){(void)c;assert(x+w<=480 && y<320);}
void LCD_DrawFastVLine(int16_t x,int16_t y,int16_t h,u16 c){(void)c;assert(x>=0 && y>=0 && x<480 && y+h<=320);}
#include "src/pages/320x240x16/touch_test_page.c"
int main(void){
 PAGE_TouchTestInit(0);assert(started==1 && status_count==4 && actions==3 && draw_canvas);
 for(ms=50;ms<500;ms+=50)PAGE_TouchTestEvent();assert(!redraws);
 tx15_touch_report.state=TX15_TOUCH_READY;tx15_touch_report.points=1;
 tx15_touch_report.x=479;tx15_touch_report.y=319;ms+=50;PAGE_TouchTestEvent();assert(redraws);
 draw_canvas(NULL,NULL);assert(canvas_draws);
 callbacks[2](NULL,-1,arguments[2]);assert(mapped==1);
 callbacks[1](NULL,-1,arguments[1]);assert(stopped==1);
 callbacks[0](NULL,-1,arguments[0]);assert(started==2);
 PAGE_TouchTestExit();assert(stopped==2);
 return 0;
}''',[])
