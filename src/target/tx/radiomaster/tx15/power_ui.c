/* Native countdown modal. RF/input services continue; GUI/Lua callers resume
 * unchanged on cancellation. No model writes until PWR_Shutdown commits. */
#include "common.h"
#include "power_ui.h"
#ifdef TX15_STANDALONE
#include "runtime.h"
#include "../../../../../hardware/tx15/board/power.h"
#include "../../../../../hardware/tx15/boot/power_button.h"
#include "../../../../../hardware/tx15/board/display.h"
#ifndef TX15_POWER_UI_MEMORY
#define TX15_POWER_UI_MEMORY(a) ((volatile uint16_t *)(uintptr_t)(a))
#endif
#ifndef TX15_POWER_UI_PIXEL
#define TX15_POWER_UI_PIXEL(x,y,c) \
    (TX15_POWER_UI_MEMORY(TX15_LCD_FB)[tx15_display_offset(x,y)]=(c))
#endif
/* Runtime-only reuse of expired USB updater shadow / RAM-chain source. Normal
 * app resources end at D0100000, optional display shadow at D014B000. This
 * 138240-byte snapshot owns D0200000..D0221C00 only while the modal is active. */
#define BACKUP 0xd0200000u
enum {LEFT=60,TOP=64,WIDTH=360,HEIGHT=192,BG=0x1082,WHITE=0xffff,ACCENT=0xfd20};
static struct tx15_power_button power_button;
static unsigned power_busy;
/* Same purpose-built 5x7 glyphs used by the native boot screen. */
static const uint8_t glyphs[][5]={
 {62,81,73,69,62},{0,66,127,64,0},{66,97,81,73,70},{33,65,69,75,49},
 {24,20,18,127,16},{39,69,69,69,57},{60,74,73,73,48},{1,113,9,5,3},
 {54,73,73,73,54},{6,73,73,41,30},
 {126,9,9,9,126},{127,73,73,73,54},{62,65,65,65,34},{127,65,65,34,28},
 {127,73,73,73,65},{127,9,9,9,1},{62,65,73,73,122},{127,8,8,8,127},
 {0,65,127,65,0},{32,64,65,63,1},{127,8,20,34,65},{127,64,64,64,64},
 {127,2,12,2,127},{127,2,4,8,127},{62,65,65,65,62},{127,9,9,9,6},
 {62,65,81,33,94},{127,9,25,41,70},{38,73,73,73,50},{1,1,127,1,1},
 {63,64,64,64,63},{31,32,64,32,31},{127,32,24,32,127},{99,20,8,20,99},
 {3,4,120,4,3},{97,81,73,69,67}};
static void service(void){(void)tx15_runtime_poll(CLOCK_getms());}
static void snapshot(unsigned restore) {
    volatile uint16_t *frame=TX15_POWER_UI_MEMORY(TX15_LCD_FB);
    volatile uint16_t *copy=TX15_POWER_UI_MEMORY(BACKUP);
    for(unsigned y=0;y<HEIGHT;y++) {
        for(unsigned x=0;x<WIDTH;x++) {
            unsigned at=tx15_display_offset(LEFT+x,TOP+y),saved=y*WIDTH+x;
            if(restore)frame[at]=copy[saved];else copy[saved]=frame[at];
        }
        if(!(y&7u))service();
    }
}
static void rect(unsigned x,unsigned y,unsigned w,unsigned h,uint16_t color) {
    for(unsigned j=0;j<h;j++) {
        for(unsigned i=0;i<w;i++)TX15_POWER_UI_PIXEL(x+i,y+j,color);
        if(w>=64 && !(j&7u))service();
    }
}
static void text(unsigned y,const char *s,unsigned scale,uint16_t color) {
    unsigned x=(480u-(unsigned)strlen(s)*6u*scale)/2u;
    for(;*s;s++,x+=6*scale) {
        int k=*s>='0'&&*s<='9'?*s-'0':(*s>='A'&&*s<='Z'?10+*s-'A':-1);
        if(k<0)continue;
        for(unsigned i=0;i<5;i++)for(unsigned j=0;j<7;j++)
            if(glyphs[k][i]&(1u<<j))rect(x+i*scale,y+j*scale,scale,scale,color);
    }
}
static void begin(void) {
    rect(LEFT,TOP,WIDTH,HEIGHT,BG);
    rect(LEFT,TOP,WIDTH,3,ACCENT);
    text(82,"POWER OFF",3,WHITE);
    rect(90,190,300,8,0x4208);
    text(218,"RELEASE TO CANCEL",2,0xbdf7);
}
static void saving(void) {
    rect(90,116,300,60,BG);text(132,"SAVING",3,WHITE);
    rect(90,190,300,8,ACCENT);
    rect(90,212,300,26,BG);text(218,"PLEASE WAIT",2,0xbdf7);
}
void tx15_power_ui_poll(void) {
    if(power_busy || power_button.shutdown)return;
    uint32_t now=CLOCK_getms();
    int pressed=(tx15_power_status()&TX15_BUTTON_PRESSED)!=0;
    (void)tx15_power_button_poll(&power_button,now,pressed);
    if(!power_button.released || !power_button.tracking || !pressed)return;
    power_busy=1; /* Protect watchdog reentry from any rendering/service path. */
    snapshot(0);begin();
    unsigned last_second=0,last_width=0;
    for(;;) {
        service();now=CLOCK_getms();
        pressed=(tx15_power_status()&TX15_BUTTON_PRESSED)!=0;
        if(tx15_power_button_poll(&power_button,now,pressed)) {
            saving();PWR_Shutdown();power_busy=0;return;
        }
        if(!pressed) {snapshot(1);power_busy=0;return;}
        uint32_t elapsed=now-power_button.since;
        unsigned seconds=(TX15_POWER_HOLD_MS-elapsed+999u)/1000u;
        unsigned width=(elapsed/50u)*300u/(TX15_POWER_HOLD_MS/50u);
        if(seconds!=last_second) {
            rect(208,116,64,60,BG);
            char value[2]={(char)('0'+seconds),0};text(120,value,7,WHITE);
            last_second=seconds;
        }
        if(width>last_width) {
            rect(90+last_width,190,width-last_width,8,ACCENT);last_width=width;
        }
    }
}
#else
void tx15_power_ui_poll(void){}
#endif
