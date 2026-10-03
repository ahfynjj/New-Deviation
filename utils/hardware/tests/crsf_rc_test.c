#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "crsf_rc.h"
static unsigned frames;
static int busy;
static struct crsf_frame last;
static int send(void *ctx,const uint8_t *data,unsigned size) {
    (void)ctx;if(busy)return 0;
    memcpy(last.bytes,data,size);last.size=size;frames++;return 1;
}
int main(void) {
    struct crsf_rc rc;int32_t ch[16]={10000,-10000,0,5000,-10000};
    crsf_rc_init(&rc);crsf_rc_tick(&rc,0,send,0);assert(!frames);
    assert(!crsf_rc_select(&rc,1,0)); /* Unimplemented external hardware fails closed. */
    assert(crsf_rc_select(&rc,0,100));
    assert(!crsf_rc_publish(&rc,ch,0,100));
    assert(crsf_rc_publish(&rc,ch,16,100));
    crsf_rc_tick(&rc,100,send,0);assert(frames==1 && crsf_frame_valid(&last));
    assert(last.size==26 && last.bytes[2]==0x16);
    assert(!crsf_rc_tools_ready(&rc,102));
    assert(crsf_rc_tools_ready(&rc,101));
    for(uint32_t t=101;t<200;t++)crsf_rc_tick(&rc,t,send,0);
    assert(frames==25 && rc.report.max_gap_ms==4); /* No Lua/main calls for 99 ms. */
    crsf_rc_tick(&rc,200,send,0);assert(frames==25 && rc.report.stale==1);
    assert(crsf_rc_tools_ready(&rc,200));
    ch[0]=-10000;assert(crsf_rc_publish(&rc,ch,16,201));
    busy=1;crsf_rc_tick(&rc,201,send,0);assert(frames==25);
    ch[0]=5000;assert(crsf_rc_publish(&rc,ch,16,202));
    busy=0;crsf_rc_tick(&rc,202,send,0);assert(frames==26);
    assert((last.bytes[3]|((last.bytes[4]&7)<<8))==1392);
    crsf_rc_select(&rc,-1,203);crsf_rc_tick(&rc,204,send,0);assert(frames==26);
    assert(!crsf_rc_publish(&rc,ch,16,204));
    assert(crsf_rc_select(&rc,0,UINT32_MAX-2));
    assert(crsf_rc_publish(&rc,ch,16,UINT32_MAX-2));
    crsf_rc_tick(&rc,UINT32_MAX-2,send,0);crsf_rc_tick(&rc,1,send,0);
    assert(frames==28 && rc.report.max_gap_ms==4);
    crsf_rc_tick(&rc,97,send,0);assert(frames==28 && rc.report.stale==1);
}
