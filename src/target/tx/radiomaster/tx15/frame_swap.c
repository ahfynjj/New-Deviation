/* Native LTDC VBR + DMA2D frame ownership. No HAL dependency.
 * Register layouts checked against ST CMSIS stm32h750xx.h and H7 HAL drivers.
 * Only built into standalone applications, after loader staging has expired.
 * Caches/MPU off is the existing native boot contract. GPL-3.0-or-later. */
#include "frame_swap.h"
#include "../../../../../hardware/tx15/board/display.h"
#ifndef TX15_FRAME_READ
#define TX15_FRAME_READ(a) (*(volatile uint32_t *)(uintptr_t)(a))
#define TX15_FRAME_WRITE(a,v) (*(volatile uint32_t *)(uintptr_t)(a)=(v))
#endif
#ifndef TX15_FRAME_MEMORY
#define TX15_FRAME_MEMORY(a) ((volatile uint32_t *)(uintptr_t)(a))
#endif
#ifndef TX15_FRAME_CYCLES
#define TX15_FRAME_CYCLES() TX15_FRAME_READ(0xe0001004u)
#endif
#ifndef TX15_FRAME_BARRIER
#define TX15_FRAME_BARRIER() __asm volatile("dsb" ::: "memory")
#endif
#define FRAME_LTDC 0x50001000u
#define FRAME_DMA 0x52001000u
#define FRAME_CLOCK 0x580244d4u
#define FRAME_RESET 0x5802447cu
#define FRAME_DEADLINE (40u*128000u)
volatile struct tx15_frame_report tx15_frame_report;
static uint32_t frame_front=TX15_LCD_FB,frame_back=TX15_FRAME_BACK;
static unsigned frame_dirty,frame_busy,frame_cpu;
static void (*frame_hook)(void);
static uint32_t frame_serviced;
int tx15_frame_ready(void){return tx15_frame_report.state==1;}
uint32_t tx15_frame_draw_address(void){return frame_back;}
uint32_t tx15_frame_visible_address(void){return frame_front;}
void tx15_frame_set_service(void (*hook)(void)){
    frame_hook=hook;frame_serviced=TX15_FRAME_CYCLES();
}
void tx15_frame_service(void){
    uint32_t now=TX15_FRAME_CYCLES(),gap=now-frame_serviced;
    if(!frame_hook || gap<128000u)return;
    if(gap>tx15_frame_report.max_service_gap_cycles)tx15_frame_report.max_service_gap_cycles=gap;
    frame_serviced=now;
    frame_busy++;frame_hook();frame_busy--;
}
static void frame_copy(void){
    uint32_t started=TX15_FRAME_CYCLES();
    if(!frame_cpu){
        TX15_FRAME_WRITE(FRAME_DMA,0); /* M2M, interrupts off */
        TX15_FRAME_WRITE(FRAME_DMA+8,0x3fu);
        TX15_FRAME_WRITE(FRAME_DMA+0x0c,frame_front);
        TX15_FRAME_WRITE(FRAME_DMA+0x10,0);
        TX15_FRAME_WRITE(FRAME_DMA+0x1c,2); /* RGB565 foreground */
        TX15_FRAME_WRITE(FRAME_DMA+0x34,2); /* RGB565 output */
        TX15_FRAME_WRITE(FRAME_DMA+0x3c,frame_back);
        TX15_FRAME_WRITE(FRAME_DMA+0x40,0);
        TX15_FRAME_WRITE(FRAME_DMA+0x44,(480u<<16)|320u);
        TX15_FRAME_BARRIER();TX15_FRAME_WRITE(FRAME_DMA,1);
        unsigned completed=0;
        for(unsigned budget=500000;budget;budget--){
            uint32_t status=TX15_FRAME_READ(FRAME_DMA+4);
            if(status&0x21u)break; /* transfer/configuration error */
            if((status&2u) && !(TX15_FRAME_READ(FRAME_DMA)&1u)){completed=1;break;}
            tx15_frame_service();
            if((uint32_t)(TX15_FRAME_CYCLES()-started)>=FRAME_DEADLINE)break;
        }
        if(!completed){
            /* Stop DMA bus writes before CPU touches its destination. Only
             * DMA2D reset is owned here; DMA1 audio and SDMMC are untouched. */
            uint32_t reset=TX15_FRAME_READ(FRAME_RESET);
            TX15_FRAME_WRITE(FRAME_RESET,reset|16u);(void)TX15_FRAME_READ(FRAME_RESET);
            TX15_FRAME_WRITE(FRAME_RESET,reset&~16u);TX15_FRAME_BARRIER();
            frame_cpu=1;tx15_frame_report.dma_errors++;
        }
    }
    if(frame_cpu){
        const volatile uint32_t *src=TX15_FRAME_MEMORY(frame_front);
        volatile uint32_t *dst=TX15_FRAME_MEMORY(frame_back);
        for(unsigned i=0;i<TX15_LCD_BYTES/4;i++){
            dst[i]=src[i];
            if(i%1920u==1919u)tx15_frame_service();
        }
        tx15_frame_report.cpu_copies++;
    }
    TX15_FRAME_BARRIER();
    uint32_t elapsed=TX15_FRAME_CYCLES()-started;
    if(elapsed>tx15_frame_report.max_copy_cycles)tx15_frame_report.max_copy_cycles=elapsed;
}
int tx15_frame_init(void){
    if(tx15_frame_report.state)return !tx15_frame_ready();
    /* Do not change panel scan order, pitch, PLL, backlight or IRQ ownership. */
    if(!(TX15_FRAME_READ(FRAME_LTDC+0x18)&1u)
        || TX15_FRAME_READ(FRAME_LTDC+0xac)!=TX15_LCD_FB
        || (TX15_FRAME_READ(FRAME_LTDC+0x24)&3u)
        || TX15_FRAME_READ(FRAME_LTDC+0x94)!=2u
        || TX15_FRAME_READ(FRAME_LTDC+0xb0)!=((640u<<16)|647u)
        || TX15_FRAME_READ(FRAME_LTDC+0xb4)!=480u){
        tx15_frame_report.state=2;return 1;
    }
    TX15_FRAME_WRITE(FRAME_CLOCK,TX15_FRAME_READ(FRAME_CLOCK)|16u);
    (void)TX15_FRAME_READ(FRAME_CLOCK);
    if(TX15_FRAME_READ(FRAME_DMA)&1u){tx15_frame_report.state=2;return 1;}
    frame_busy++;frame_copy();frame_busy--;
    tx15_frame_report.ltdc_status=TX15_FRAME_READ(FRAME_LTDC+0x38);
    tx15_frame_report.state=1;return 0;
}
void tx15_frame_damage(void){if(tx15_frame_ready())frame_dirty=1;}
void tx15_frame_pixel(unsigned x,unsigned y,uint16_t color){
    if(!tx15_frame_ready() || x>=480 || y>=320)return;
    ((volatile uint16_t *)TX15_FRAME_MEMORY(frame_back))[y*480+x]=color;frame_dirty=1;
}
void tx15_frame_rect(unsigned x,unsigned y,unsigned w,unsigned h,uint16_t color){
    if(!tx15_frame_ready() || x>=480 || y>=320 || !w || !h)return;
    if(w>480-x)w=480-x;
    if(h>320-y)h=320-y;
    uint32_t pair=(uint32_t)color|((uint32_t)color<<16);
    frame_busy++;
    for(unsigned row=y;row<y+h;row++){
        volatile uint16_t *p=(volatile uint16_t *)TX15_FRAME_MEMORY(frame_back)+row*480+x;
        unsigned n=w;
        if(x&1u){*p++=color;n--;}
        volatile uint32_t *words=(volatile uint32_t *)p;
        while(n>=2){*words++=pair;n-=2;}
        if(n)*(volatile uint16_t *)words=color;
        if(!(row&7u))tx15_frame_service();
    }
    frame_dirty=1;frame_busy--;
}
void tx15_frame_present(void){
    if(frame_busy || !tx15_frame_ready() || !frame_dirty)return;
    frame_busy++;uint32_t started=TX15_FRAME_CYCLES();
    TX15_FRAME_BARRIER();
    TX15_FRAME_WRITE(FRAME_LTDC+0xac,frame_back);
    TX15_FRAME_WRITE(FRAME_LTDC+0x24,2); /* vertical blank, never immediate */
    unsigned acknowledged=0;
    for(unsigned budget=500000;budget;budget--){
        if(!(TX15_FRAME_READ(FRAME_LTDC+0x24)&3u)){acknowledged=1;break;}
        tx15_frame_service();
        if((uint32_t)(TX15_FRAME_CYCLES()-started)>=FRAME_DEADLINE)break;
    }
    uint32_t elapsed=TX15_FRAME_CYCLES()-started;
    if(elapsed>tx15_frame_report.max_wait_cycles)tx15_frame_report.max_wait_cycles=elapsed;
    tx15_frame_report.ltdc_status|=TX15_FRAME_READ(FRAME_LTDC+0x38);
    if(!acknowledged){
        /* Request may still latch later. Freeze both buffers rather than
         * exposing a partially repainted pending frame. Main services live on. */
        tx15_frame_report.state=2;tx15_frame_report.swap_timeouts++;frame_busy--;return;
    }
    uint32_t old=frame_front;frame_front=frame_back;frame_back=old;
    TX15_FRAME_BARRIER();frame_copy();
    frame_dirty=0;tx15_frame_report.frames++;frame_busy--;
}
