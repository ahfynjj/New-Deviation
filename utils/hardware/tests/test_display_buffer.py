"""Completed regions are submitted without displaying erase/redraw intermediates."""
import unittest
import test_controls as controls
import test_switch_upgrade as switches
from pathlib import Path
class DisplayBufferTests(unittest.TestCase):
    compile_run=controls.ControlsTests.compile_run
    run_c=switches.SwitchUpgradeTests.run_c
    def test_real_lcd_present_and_lua_fill_share_hidden_buffer(self):
        root=Path(__file__).resolve().parents[3]
        lua=(root/'src/target/tx/radiomaster/tx15/lua_tool.c').read_text()
        fill=lua[lua.index('static void fill('):lua.index('static void clear(')]
        self.run_c(r'''
#include <assert.h>
#define TX15_BUFFERED_DISPLAY 1
#include "common.h"
#include "hardware/tx15/board/display_buffer.h"
static uint16_t front_pixels[TX15_LCD_BYTES/2],shadow_pixels[TX15_LCD_BYTES/2];
#define TX15_DISPLAY_MEMORY(a) ((a)==TX15_LCD_FB?front_pixels:shadow_pixels)
#define TX15_DISPLAY_BARRIER() ((void)0)
#include "hardware/tx15/board/display_buffer.c"
void tx15_display_pixel(unsigned x,unsigned y,uint16_t c){tx15_display_buffer_pixel(x,y,c);}
#include "src/target/tx/radiomaster/tx15/lcd.c"
'''+fill+r'''
int main(void){
 tx15_display_buffer_init();LCD_DrawStart(1,2,2,2,DRAW_NWSE);
 LCD_DrawPixel(0x1234);LCD_DrawPixel(0x5678);LCD_DrawStop();
 assert(!front_pixels[2*480+1] && !front_pixels[2*480+2]);
 LCD_ForceUpdate();assert(front_pixels[2*480+1]==0x1234 && front_pixels[2*480+2]==0x5678);
 fill(-2,-2,5,5,0xffff);assert(!front_pixels[0] && front_pixels[2*480+1]==0x1234);
 LCD_ForceUpdate();assert(front_pixels[0]==0xffff && front_pixels[2*480+2]==0xffff && !front_pixels[3]);
 return 0;
}''',[])
    def test_hidden_redraw_dirty_clip_and_bounded_service(self):
        self.compile_run(r'''
#include <assert.h>
#include <stdint.h>
#include "hardware/tx15/board/display_buffer.h"
static uint16_t front[TX15_LCD_BYTES/2],back[TX15_LCD_BYTES/2];
static unsigned services;
static volatile uint16_t *memory(uint32_t a){assert(a==TX15_LCD_FB || a==TX15_LCD_SHADOW);return a==TX15_LCD_FB?front:back;}
#define TX15_DISPLAY_MEMORY(a) memory(a)
#define TX15_DISPLAY_BARRIER() ((void)0)
#include "hardware/tx15/board/display_buffer.c"
static void service(void){services++;tx15_display_buffer_flush();} /* reentrant present is a no-op */
int main(void){
 assert(TX15_LCD_FB+TX15_LCD_BYTES<=0xd0080000u);
 assert(TX15_LCD_SHADOW>=0xd0100000u && TX15_LCD_SHADOW+TX15_LCD_BYTES<=0xd0200000u);
 for(unsigned i=0;i<TX15_LCD_BYTES/2;i++)front[i]=0x1234;
 tx15_display_buffer_init();tx15_display_buffer_set_service(service);
 tx15_display_buffer_rect(10,10,5,5,0); /* erase behind a changing label */
 tx15_display_buffer_pixel(12,12,0xffff); /* draw new glyph */
 for(unsigned i=0;i<TX15_LCD_BYTES/2;i++)assert(front[i]==0x1234);
 tx15_display_buffer_flush();assert(tx15_display_buffer_report.last_pixels==25);
 assert(front[12*480+12]==0xffff && front[10*480+10]==0 && front[9*480+10]==0x1234);
 unsigned frames=tx15_display_buffer_report.frames;tx15_display_buffer_flush();
 assert(tx15_display_buffer_report.frames==frames);
 tx15_display_buffer_rect(479,319,0xffffffffu,0xffffffffu,0x9876);
 tx15_display_buffer_pixel(480,0,1);tx15_display_buffer_pixel(0,320,1);
 tx15_display_buffer_flush();assert(tx15_display_buffer_report.last_pixels==1 && front[153599]==0x9876);
 services=0;tx15_display_buffer_rect(0,0,480,320,0x4567);
 assert(services>=300); /* Yield during drawing, not just final submit. */
 services=0;tx15_display_buffer_flush();assert(services>=300);
 for(unsigned i=0;i<TX15_LCD_BYTES/2;i++)assert(front[i]==0x4567);
 return 0;
}''',[])
