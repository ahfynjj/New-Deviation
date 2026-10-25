/* New Deviation native TX15 application adapter; GPL-3.0-or-later. */
#include "common.h"
#include "../../../../../hardware/tx15/board/display.h"
#ifdef TX15_FRAME_SWAP
#include "frame_swap.h"
#endif
#ifdef TX15_STATUS_REGIONS
#include "display_region.h"
#endif
#ifdef TX15_BUFFERED_DISPLAY
#include "../../../../../hardware/tx15/board/display_buffer.h"
#endif
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
#ifdef TX15_STATUS_REGIONS
    if(tx15_region_active)tx15_region_pixel(x,y,(uint16_t)color);
    else
#endif
        tx15_display_pixel(x,y,(uint16_t)color);
    if(x<right) x++;
    else {
        x=left;
        if((step>0 && y==bottom)||(step<0 && y==top)) active=0;
        else y=(unsigned)((int)y+step);
    }
}
void LCD_DrawPixelXY(unsigned x0,unsigned y0,unsigned color) {
#ifdef TX15_STATUS_REGIONS
    if(tx15_region_active)tx15_region_pixel(x0,y0,(uint16_t)color);
    else
#endif
        tx15_display_pixel(x0,y0,(uint16_t)color);
}
void LCD_DrawStop(void) {
    active=0;
#ifdef TX15_FRAME_SWAP
    tx15_frame_service();
#endif
}
/* RGB panels have no character-map window hardware. Deviation's mapped
 * drawing operations use the same absolute pixel coordinates here. */
void LCD_DrawMappedStart(unsigned a,unsigned b,unsigned c,unsigned d,enum DrawDir dir) { LCD_DrawStart(a,b,c,d,dir); }
void LCD_DrawMappedPixel(unsigned c) { LCD_DrawPixel(c); }
void LCD_DrawMappedPixelXY(unsigned a,unsigned b,unsigned c) { LCD_DrawPixelXY(a,b,c); }
void LCD_DrawMappedStop(void) { LCD_DrawStop(); }
void LCD_ForceUpdate(void) {
#ifdef TX15_FRAME_SWAP
    tx15_frame_present();
#elif defined(TX15_BUFFERED_DISPLAY)
    tx15_display_buffer_flush();
#endif
}
