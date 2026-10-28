"""Actual raster primitives must use existing bounded hidden-frame bulk writes."""
import unittest
import test_switch_upgrade as helper

class BulkRasterTests(unittest.TestCase):
    run_c=helper.SwitchUpgradeTests.run_c
    def test_native_fill_lines_roundrect_clipping_and_no_pixel_loop(self):
        self.run_c(r'''
#include <assert.h>
#include <string.h>
#define TX15_FRAME_SWAP 1
#include "common.h"
static uint16_t frame[320][480];
static unsigned bulk,pixels,services,x0,y0,x1,y1,cx,cy;
void tx15_frame_rect(unsigned x,unsigned y,unsigned w,unsigned h,uint16_t c){
 bulk++;if(x>=480 || y>=320)return;
 if(w>480-x)w=480-x;if(h>320-y)h=320-y;
 for(unsigned j=y;j<y+h;j++)for(unsigned i=x;i<x+w;i++)frame[j][i]=c;
}
void tx15_frame_service(void){services++;}
void LCD_DrawStart(unsigned x,unsigned y,unsigned a,unsigned b,enum DrawDir d){(void)d;x0=cx=x;y0=cy=y;x1=a;y1=b;}
void LCD_DrawPixel(unsigned c){pixels++;if(cx<480 && cy<320)frame[cy][cx]=c;if(cx<x1)cx++;else{cx=x0;cy++;}}
void LCD_DrawPixelXY(unsigned x,unsigned y,unsigned c){pixels++;if(x<480 && y<320)frame[y][x]=c;}
void LCD_DrawStop(void){}
#include "src/screen/320x240x16/lcd_gfx.c"
int main(void){
 LCD_FillRect(12,52,146,96,0xabcd);
 assert(bulk==1 && !pixels && services);
 assert(frame[52][12]==0xabcd && frame[147][157]==0xabcd && !frame[148][157]);
 LCD_DrawFastHLine(478,319,8,0x1111);assert(frame[319][478]==0x1111 && frame[319][479]==0x1111);
 LCD_DrawFastVLine(3,-2,5,0x2222);assert(frame[0][3]==0x2222 && frame[2][3]==0x2222 && !frame[3][3]);
 unsigned before=bulk;
 LCD_FillRect(0,0,0,20,1);LCD_DrawFastHLine(0,0,0,1);LCD_DrawFastVLine(0,0,0,1);LCD_DrawFastVLine(-1,0,4,1);
 assert(bulk==before && !pixels);
 LCD_FillRoundRect(12,52,146,96,7,0x5555);
 assert(!pixels && bulk-before<40);
 assert(frame[60][30]==0x5555 && frame[52][12]==0xabcd);
 return 0;
}''',[])
