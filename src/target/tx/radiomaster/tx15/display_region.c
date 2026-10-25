/* Complete short labels off-screen, then copy only that rectangle. No global
 * shadow compare/dirty-bounds scan, IRQ changes, clock writes or frame wait. */
#include "display_region.h"
#include "../../../../../hardware/tx15/board/display.h"
#ifndef TX15_REGION_MEMORY
#define TX15_REGION_MEMORY(a) ((volatile uint16_t *)(uintptr_t)(a))
#endif
#ifndef TX15_REGION_CYCLES
#define TX15_REGION_CYCLES() (*(volatile uint32_t *)0xe0001004u)
#endif
#ifndef TX15_REGION_BARRIER
#define TX15_REGION_BARRIER() __asm volatile("dsb" ::: "memory")
#endif
volatile struct tx15_region_report tx15_region_report;
unsigned tx15_region_active;
static unsigned region_left,region_top,region_width,region_height;
static uint32_t draw_started;
/* Thirty KiB at D0300000, beyond resources, display shadow and power modal.
 * Both buffers retain 480-pixel pitch, so word-copy alignment always agrees. */
static void copy_span(volatile uint16_t *dst,const volatile uint16_t *src,unsigned n) {
    if(n && ((uintptr_t)dst&3u)) {*dst++=*src++;n--;}
    volatile uint32_t *out=(volatile uint32_t *)dst;
    const volatile uint32_t *in=(const volatile uint32_t *)src;
    while(n>=2) {*out++=*in++;n-=2;}
    if(n)*(volatile uint16_t *)out=*(const volatile uint16_t *)in;
}
int tx15_region_begin(unsigned x,unsigned y,unsigned w,unsigned h) {
    if(tx15_region_active || !w || !h || x>=TX15_LCD_WIDTH || y>=TX15_LCD_HEIGHT)return 0;
    if(w>TX15_LCD_WIDTH-x)w=TX15_LCD_WIDTH-x;
    if(h>TX15_LCD_HEIGHT-y)h=TX15_LCD_HEIGHT-y;
    if(h>TX15_REGION_ROWS)return 0;
    draw_started=TX15_REGION_CYCLES();
    region_left=x;region_top=y;region_width=w;region_height=h;
    const volatile uint16_t *front=TX15_REGION_MEMORY(TX15_LCD_FB);
    volatile uint16_t *tile=TX15_REGION_MEMORY(TX15_REGION_SCRATCH);
    for(unsigned row=0;row<h;row++)
        copy_span(tile+row*TX15_LCD_WIDTH+x,front+(y+row)*TX15_LCD_WIDTH+x,w);
    tx15_region_active=1;return 1;
}
void tx15_region_pixel(unsigned x,unsigned y,uint16_t color) {
    if(x>=region_left && x-region_left<region_width && y>=region_top && y-region_top<region_height)
        TX15_REGION_MEMORY(TX15_REGION_SCRATCH)[(y-region_top)*TX15_LCD_WIDTH+x]=color;
}
void tx15_region_end(void) {
    if(!tx15_region_active)return;
    uint32_t start=TX15_REGION_CYCLES(),draw=start-draw_started;
    volatile uint16_t *front=TX15_REGION_MEMORY(TX15_LCD_FB);
    const volatile uint16_t *tile=TX15_REGION_MEMORY(TX15_REGION_SCRATCH);
    for(unsigned row=0;row<region_height;row++)
        copy_span(front+(region_top+row)*TX15_LCD_WIDTH+region_left,
                  tile+row*TX15_LCD_WIDTH+region_left,region_width);
    TX15_REGION_BARRIER();
    tx15_region_active=0;
    uint32_t commit=TX15_REGION_CYCLES()-start;
    if(draw>tx15_region_report.max_draw_cycles)tx15_region_report.max_draw_cycles=draw;
    if(commit>tx15_region_report.max_commit_cycles)tx15_region_report.max_commit_cycles=commit;
    tx15_region_report.frames++;tx15_region_report.pixels+=region_width*region_height;
}
