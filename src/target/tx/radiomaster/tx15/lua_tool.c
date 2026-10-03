/* Official ELRS Lua on native TX15 display/input; GPL-3.0-or-later. */
#ifdef TX15_ELRS_LUA
#include "common.h"
#include "buttons.h"
#include "mixer.h"
#include "gui/gui.h"
#include "config/display.h"
#include "romfs.h"
#include "rf_lua.h"
#include "lua/runner.h"
#include "../../../../../hardware/tx15/board/display.h"
static union { double align; unsigned char bytes[160*1024]; } heap;
static struct nd_lua tool;
/* Address obtained from ELF symbols for host diagnostics, never hard-coded. */
volatile struct {u32 state,runs,used,peak,max_ms,blocked_writes;char error[160];} tx15_lua_report;
static buttonAction_t action;
static unsigned events[8],head,count,leave;
static void service(void *ctx) { (void)ctx;tx15_rf_lua_poll(); }
static uint32_t now(void *ctx) { (void)ctx;return CLOCK_getms(); }
static void stop(void *ctx) { (void)ctx;tx15_rf_lua_stop(); }
static u8 select_font(unsigned flags)
{ return LCD_SetFont(flags&ND_MIDSIZE?LABEL_FONT.font:DEFAULT_FONT.font); }
static void dimensions(void *ctx,const char *s,unsigned flags,int *w,int *h)
{
    (void)ctx;u8 old=select_font(flags);u16 width,height;
    LCD_GetStringDimensions((const u8 *)s,&width,&height);LCD_SetFont(old);
    *w=width;*h=height;
}
static void fill(int x,int y,int w,int h,u16 color)
{
    int right=x+w,bottom=y+h;if(x<0)x=0;if(y<0)y=0;
    if(right>480)right=480;
    if(bottom>320)bottom=320;
    if(x>=right || y>=bottom) return;
    for(int row=y;row<bottom;row++) {
        volatile u16 *p=(volatile u16 *)TX15_LCD_FB+row*480+x;
        for(int column=x;column<right;column++) *p++=color;
        if(!(row&7)) tx15_rf_lua_poll();
    }
}
static void clear(void *ctx) { (void)ctx;fill(0,0,480,320,0xffff); }
static void rect(void *ctx,int x,int y,int w,int h,u16 color,int solid)
{
    (void)ctx;
    if(solid) fill(x,y,w,h,color);
    else {fill(x,y,w,1,color);fill(x,y+h-1,w,1,color);fill(x,y,1,h,color);fill(x+w-1,y,1,h,color);}
}
static void line(void *ctx,int x,int y,int x2,int y2,u16 color)
{
    (void)ctx;
    int dx=x2>x?x2-x:x-x2,sx=x<x2?1:-1,dy=y2>y?y-y2:y2-y,sy=y<y2?1:-1,error=dx+dy;
    for(unsigned n=0;n<4096;n++) {
        if(x>=0 && x<480 && y>=0 && y<320) tx15_display_pixel(x,y,color);
        if(x==x2 && y==y2) break;
        int twice=2*error;if(twice>=dy) {error+=dy;x+=sx;}if(twice<=dx) {error+=dx;y+=sy;}
    }
}
static void text(void *ctx,int x,int y,const char *s,unsigned flags,u16 color)
{
    (void)ctx;u8 old=select_font(flags);u16 width,height;
    LCD_GetStringDimensions((const u8 *)s,&width,&height);
    if(flags&ND_INVERS) {fill(x,y,width,height,0);color=0xffff;}
    if(x>=0 && y>=0 && x<480 && y<320 && (!(flags&ND_BLINK) || (CLOCK_getms()/400)%2==0)) {
        LCD_SetFontColor(color);LCD_PrintStringXY(x,y,s);
        if(flags&ND_BOLD) LCD_PrintStringXY(x+1,y,s);
    }
    LCD_SetFont(old);tx15_rf_lua_poll();
}
static unsigned button(u32 buttons,unsigned flags,void *ctx)
{
    (void)ctx;
    if((buttons&CHAN_ButtonMask(BUT_EXIT)) && (flags&BUTTON_LONGPRESS)) {leave=1;return 1;}
    unsigned event=0;
    if(flags&BUTTON_PRESS) {
        if(buttons&CHAN_ButtonMask(BUT_UP)) event=ND_EVT_PREV;
        else if(buttons&CHAN_ButtonMask(BUT_DOWN)) event=ND_EVT_NEXT;
        else if(buttons&CHAN_ButtonMask(BUT_LEFT)) event=ND_EVT_PREV;
        else if(buttons&CHAN_ButtonMask(BUT_RIGHT)) event=ND_EVT_NEXT;
    }
    if((flags&BUTTON_RELEASE) && !(flags&BUTTON_HAD_LONGPRESS)) {
        if(buttons&CHAN_ButtonMask(BUT_ENTER)) event=ND_EVT_ENTER;
        else if(buttons&CHAN_ButtonMask(BUT_EXIT)) event=ND_EVT_EXIT;
    }
    if(event && count<8) {events[(head+count)%8]=event;count++;}
    return 1;
}
void tx15_lua_tool(void)
{
    const struct tx15_resource *script=NULL;
    for(size_t i=0;i<tx15_resource_count;i++) if(!strcmp(tx15_resources[i].path,"scripts/elrs.lua")) script=&tx15_resources[i];
    if(!script) return;
    struct nd_lua_host host={.clock_ms=now,.service=service,.clear=clear,.text=text,
        .size_text=dimensions,.rect=rect,.line=line,.stop=stop};
    head=count=leave=0;
    BUTTON_RegisterCallback(&action,CHAN_ButtonMask(BUT_ENTER)|CHAN_ButtonMask(BUT_EXIT)|
        CHAN_ButtonMask(BUT_UP)|CHAN_ButtonMask(BUT_DOWN)|CHAN_ButtonMask(BUT_LEFT)|CHAN_ButtonMask(BUT_RIGHT),
        BUTTON_PRESS|BUTTON_RELEASE|BUTTON_LONGPRESS|BUTTON_PRIORITY,button,NULL);
    u32 started=CLOCK_getms(),previous=started;
    nd_lua_start(&tool,heap.bytes,sizeof(heap.bytes),&host,tx15_rf_lua_init(),(const char *)script->data,script->size);
    for(;;) {
        CLOCK_ResetWatchdog();BUTTON_Handler();u32 ms=CLOCK_getms();
        if(ms-previous>=20) {
            previous=ms;MIXER_CalcChannels();unsigned event=0;
            if(count) {event=events[head];head=(head+1)%8;count--;}
            nd_lua_run(&tool,event);
            tx15_lua_report.state=tool.state;tx15_lua_report.runs=tool.runs;
            tx15_lua_report.used=tool.arena.used;tx15_lua_report.peak=tool.arena.peak;
            tx15_lua_report.max_ms=tool.max_ms;tx15_lua_report.blocked_writes=tool.blocked_writes;
            memcpy((void *)tx15_lua_report.error,tool.error,sizeof(tool.error));
            if(tool.state==ND_LUA_ERROR) {
                clear(NULL);text(NULL,5,50,"Lua stopped",ND_BOLD,0);text(NULL,5,90,tool.error,0,0);
                break;
            }
        }
        if(leave || tool.state==ND_LUA_EXITED || ms-started>=120000) break;
    }
    nd_lua_close(&tool);tx15_rf_lua_stop();BUTTON_UnregisterCallback(&action);
    LCD_SetFont(DEFAULT_FONT.font);LCD_SetFontColor(DEFAULT_FONT.font_color);
    GUI_DrawScreen();
}
#endif
