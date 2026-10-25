"""Real label helper keeps erase/repaint off the scanout until completion."""
import unittest
import test_switch_upgrade as switches

class DisplayRegionTests(unittest.TestCase):
    run_c=switches.SwitchUpgradeTests.run_c
    def test_actual_label_is_composed_before_visible_row_commit(self):
        self.run_c(r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#define TX15_STATUS_REGIONS 1
#include "common.h"
#include "gui/gui.h"
#include "config/display.h"
static uint16_t front[480*320],tile[480*32];
static unsigned ticks,paints,expect_composed;
static uint16_t *memory(uint32_t a){
 if(a==0xd0000000)return front;assert(a==0xd0300000);return tile;
}
#define TX15_REGION_MEMORY(a) memory(a)
#define TX15_REGION_CYCLES() (++ticks)
#define TX15_REGION_BARRIER() ((void)0)
#include "src/target/tx/radiomaster/tx15/display_region.c"
#include "src/target/tx/radiomaster/tx15/lcd.c"
struct display_settings Display;
void tx15_display_pixel(unsigned x,unsigned y,uint16_t c){assert(x<480 && y<320);front[y*480+x]=c;}
u8 LCD_SetFont(unsigned f){(void)f;return 0;}
void LCD_SetFontColor(u16 c){(void)c;}
void LCD_GetStringDimensions(const u8 *s,u16 *w,u16 *h){*w=strlen((const char *)s)*6;*h=12;}
void LCD_FillRect(u16 x,u16 y,u16 w,u16 h,u16 c){
 for(unsigned row=y;row<y+h;row++)for(unsigned col=x;col<x+w;col++)LCD_DrawPixelXY(col,row,c);
}
void GUI_DrawBackground(u16 x,u16 y,u16 w,u16 h){LCD_FillRect(x,y,w,h,0x2222);}
void LCD_DrawRect(u16 x,u16 y,u16 w,u16 h,u16 c){(void)x;(void)y;(void)w;(void)h;(void)c;}
void LCD_DrawFastHLine(u16 x,u16 y,u16 w,u16 c){LCD_FillRect(x,y,w,1,c);}
void LCD_PrintStringXY(unsigned x,unsigned y,const char *s){
 paints++;
 /* Background erase must not reach visible scanout before glyphs are ready. */
 if(expect_composed)for(unsigned i=0;i<480*320;i++)assert(front[i]==0x1111);
 for(unsigned row=y;row<y+12;row++)
  for(unsigned col=x;col<x+strlen(s)*6;col++)LCD_DrawPixelXY(col,row,0xf800);
}
#include "src/gui/320x240x16/_label.c"
#undef TX15_STATUS_REGIONS
#define GUI_DrawLabelHelper direct_label
#include "src/gui/320x240x16/_label.c"
#undef GUI_DrawLabelHelper
static void compare_direct(unsigned w,unsigned h,unsigned selected,unsigned align){
 static uint16_t expected[480*320];
 struct LabelDesc desc={0};desc.font=1;desc.align=align;
 Display.select_width=8;
 for(unsigned i=0;i<480*320;i++)front[i]=0x1111;
 direct_label(100,100,w,h,"LONG VALUE",&desc,selected);
 memcpy(expected,front,sizeof front);
 for(unsigned i=0;i<480*320;i++)front[i]=0x1111;
 unsigned frames=tx15_region_report.frames;
 GUI_DrawLabelHelper(100,100,w,h,"LONG VALUE",&desc,selected);
 assert(memcmp(expected,front,sizeof front)==0);
 assert(tx15_region_report.frames==frames); /* overflow must stay direct */
}
int main(void){
 for(unsigned i=0;i<480*320;i++)front[i]=0x1111;
 struct LabelDesc desc={0};desc.font=1;
 expect_composed=1;GUI_DrawLabelHelper(21,44,439,23,"DMA:7",&desc,0);expect_composed=0;
 assert(paints==1 && !tx15_region_active);
 assert(front[44*480+21]==0x2222 && front[43*480+21]==0x1111);
 assert(tx15_region_report.frames==1 && tx15_region_report.pixels==439*23);
 assert(!tx15_region_begin(0,0,480,33)); /* large objects remain direct */
 assert(!tx15_region_begin(480,0,1,1));
 assert(tx15_region_begin(479,319,20,20)); /* clipped to one pixel */
 assert(!tx15_region_begin(0,0,1,1)); /* must not disturb active region */
 LCD_DrawPixelXY(479,319,0xabcd);LCD_DrawPixelXY(0,0,0xbeef);
 assert(front[319*480+479]==0x1111 && front[0]==0x1111);
 tx15_region_end();assert(front[319*480+479]==0xabcd && front[0]==0x1111);
 assert(tx15_region_report.pixels==439*23+1);
 compare_direct(10,16,0,ALIGN_LEFT); /* legacy narrow variable label */
 compare_direct(100,8,0,ALIGN_LEFT); /* font taller than object */
 compare_direct(65,23,1,ALIGN_LEFT); /* selection inset pushes text outside */
 compare_direct(10,16,1,ALIGN_RIGHT);
 return 0;
}''',[])
