#include "display_buffer.h"
#ifndef TX15_DISPLAY_MEMORY
#define TX15_DISPLAY_MEMORY(a) ((volatile uint16_t *)(uintptr_t)(a))
#endif
#ifndef TX15_DISPLAY_BARRIER
#define TX15_DISPLAY_BARRIER() __asm volatile("dsb" ::: "memory")
#endif
volatile struct tx15_display_buffer_report tx15_display_buffer_report;
static unsigned dirty,buffer_left,buffer_right,buffer_top,buffer_bottom,busy,work;
static void (*service_hook)(void);
static void yield_pixels(void) {
    if(++work==512) {work=0;if(service_hook)service_hook();}
}
static void mark(unsigned x,unsigned y,unsigned w,unsigned h) {
    if(!dirty) {buffer_left=x;buffer_top=y;buffer_right=x+w;buffer_bottom=y+h;dirty=1;return;}
    if(x<buffer_left)buffer_left=x;
    if(y<buffer_top)buffer_top=y;
    if(x+w>buffer_right)buffer_right=x+w;
    if(y+h>buffer_bottom)buffer_bottom=y+h;
}
void tx15_display_buffer_init(void) {
    if(tx15_display_buffer_report.state)return;
    volatile uint16_t *front=TX15_DISPLAY_MEMORY(TX15_LCD_FB),*back=TX15_DISPLAY_MEMORY(TX15_LCD_SHADOW);
    for(unsigned i=0;i<TX15_LCD_BYTES/2;i++)back[i]=front[i];
    TX15_DISPLAY_BARRIER();tx15_display_buffer_report.state=1;
}
void tx15_display_buffer_set_service(void (*service)(void)) {service_hook=service;}
void tx15_display_buffer_pixel(unsigned x,unsigned y,uint16_t color) {
    if(x>=TX15_LCD_WIDTH || y>=TX15_LCD_HEIGHT)return;
    if(!tx15_display_buffer_report.state) {TX15_DISPLAY_MEMORY(TX15_LCD_FB)[tx15_display_offset(x,y)]=color;return;}
    busy=1;volatile uint16_t *p=TX15_DISPLAY_MEMORY(TX15_LCD_SHADOW)+tx15_display_offset(x,y);
    if(*p!=color) {*p=color;mark(x,y,1,1);}
    yield_pixels();busy=0;
}
void tx15_display_buffer_rect(unsigned x,unsigned y,unsigned w,unsigned h,uint16_t color) {
    if(x>=TX15_LCD_WIDTH || y>=TX15_LCD_HEIGHT || !w || !h)return;
    if(w>TX15_LCD_WIDTH-x)w=TX15_LCD_WIDTH-x;
    if(h>TX15_LCD_HEIGHT-y)h=TX15_LCD_HEIGHT-y;
    busy=1;unsigned changed=0;
    volatile uint16_t *base=TX15_DISPLAY_MEMORY(tx15_display_buffer_report.state?TX15_LCD_SHADOW:TX15_LCD_FB);
    for(unsigned row=y;row<y+h;row++) {
        volatile uint16_t *p=base+tx15_display_offset(x,row);
        for(unsigned column=0;column<w;column++) {
            if(p[column]!=color) {p[column]=color;changed=1;}
            yield_pixels();
        }
    }
    if(changed && tx15_display_buffer_report.state)mark(x,y,w,h);
    busy=0;
}
void tx15_display_buffer_flush(void) {
    if(busy || !dirty)return;
    busy=1;TX15_DISPLAY_BARRIER();
    volatile uint16_t *front=TX15_DISPLAY_MEMORY(TX15_LCD_FB),*back=TX15_DISPLAY_MEMORY(TX15_LCD_SHADOW);
    unsigned pixels=0;
    for(unsigned row=buffer_top;row<buffer_bottom;row++) {
        unsigned start=tx15_display_offset(buffer_left,row),end=start+buffer_right-buffer_left;
        for(unsigned i=start;i<end;i++) {front[i]=back[i];pixels++;yield_pixels();}
    }
    TX15_DISPLAY_BARRIER();dirty=0;busy=0;
    tx15_display_buffer_report.last_pixels=pixels;tx15_display_buffer_report.pixels+=pixels;
    tx15_display_buffer_report.frames++;
}
