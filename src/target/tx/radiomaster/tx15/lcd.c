/* New Deviation native TX15 application adapter; GPL-3.0-or-later. */
#include "common.h"
#include "../../../../../hardware/tx15/board/display.h"
static unsigned left, right, top, bottom, x, y;
static int step;
static unsigned active;
void LCD_DrawStart(unsigned x0,unsigned y0,unsigned x1,unsigned y1,enum DrawDir dir) {
    left=x0; right=x1; top=y0; bottom=y1; x=x0;
    step=(dir==DRAW_SWNE)?-1:1; y=(step<0)?y1:y0;
    active=x0<=x1 && y0<=y1;
}
void LCD_DrawPixel(unsigned color) {
    if(!active) return;
    tx15_display_pixel(x,y,(uint16_t)color);
    if(x<right) x++;
    else {
        x=left;
        if((step>0 && y==bottom)||(step<0 && y==top)) active=0;
        else y=(unsigned)((int)y+step);
    }
}
void LCD_DrawPixelXY(unsigned x0,unsigned y0,unsigned color) {
    tx15_display_pixel(x0,y0,(uint16_t)color);
}
void LCD_DrawStop(void) { active=0; }
/* RGB panels have no character-map window hardware. Deviation's mapped
 * drawing operations use the same absolute pixel coordinates here. */
void LCD_DrawMappedStart(unsigned a,unsigned b,unsigned c,unsigned d,enum DrawDir dir) { LCD_DrawStart(a,b,c,d,dir); }
void LCD_DrawMappedPixel(unsigned c) { LCD_DrawPixel(c); }
void LCD_DrawMappedPixelXY(unsigned a,unsigned b,unsigned c) { LCD_DrawPixelXY(a,b,c); }
void LCD_DrawMappedStop(void) { LCD_DrawStop(); }
void LCD_ForceUpdate(void) { /* LTDC continuously scans the uncached framebuffer. */ }
