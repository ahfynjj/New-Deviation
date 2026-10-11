/* Purpose-built glyphs; no filesystem, application UI or RF dependency. */
#include "screen.h"
#include "../board/display.h"
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
static void rect(unsigned x,unsigned y,unsigned w,unsigned h,uint16_t color)
{ for(unsigned j=0;j<h;j++)for(unsigned i=0;i<w;i++)tx15_display_pixel(x+i,y+j,color); }
static void text(unsigned x,unsigned y,const char *s,unsigned scale,uint16_t color)
{
    for(;*s;s++,x+=6*scale) {
        int k=*s>='0'&&*s<='9'?*s-'0':(*s>='A'&&*s<='Z'?10+*s-'A':-1);
        if(k<0)continue;
        for(unsigned i=0;i<5;i++)for(unsigned j=0;j<7;j++)
            if(glyphs[k][i]&(1u<<j))rect(x+i*scale,y+j*scale,scale,scale,color);
    }
}
void tx15_update_screen(const struct tx15_update_reply *s,unsigned connected,unsigned writable)
{
    static const char *const states[]={"WAITING","RECEIVING","CHECKING","READY",
        "ERASING","WRITING","VERIFYING","DONE","ERROR"};
    tx15_display_fill(0x0841);
    text(30,25,"NEW DEVIATION",4,0xffff);text(30,70,"USB UPDATE",3,0x07ff);
    text(30,125,s->state<=TX15_ERROR?states[s->state]:"ERROR",4,s->error?0xf800:0xffff);
    text(30,185,connected?"USB CONNECTED":"CONNECT DATA USB",2,0xffff);
    text(30,215,writable?"MODELS AND CALIBRATION KEPT":"READ ONLY",2,0xffff);
    text(30,285,s->state==TX15_DONE?"POWER OFF THEN ON":"KEEP POWER DURING UPDATE",2,0xffff);
    unsigned progress=s->total && s->received<=s->total?(unsigned)((uint64_t)s->received*420/s->total):0;
    rect(30,250,420,12,0x4208);rect(30,250,progress,12,0x07e0);
}
