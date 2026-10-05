#include <assert.h>
#include <string.h>
#include "target/tx/radiomaster/tx15/rf_rc.h"
#include "target/tx/radiomaster/tx15/rf_lua.h"
static unsigned frames,stops;
static uint32_t now;
static struct crsf_frame frame;
static struct crsf_link link;
static int uart_ok=1;
static unsigned ticks(unsigned i) {
    unsigned bit=i*11,word=frame.bytes[3+bit/8]|(frame.bytes[4+bit/8]<<8)|(frame.bytes[5+bit/8]<<16);
    return (word>>(bit%8))&2047;
}
uint32_t CLOCK_getms(void) {return now;}
int tx15_rf_uart_send(const uint8_t *p,unsigned n) {
    if(!uart_ok)return 0;
    memcpy(frame.bytes,p,n);frame.size=n;frames++;return 1;
}
struct crsf_link *tx15_rf_lua_select(int slot) {
    stops++;crsf_link_init(&link);if(uart_ok)crsf_link_select(&link,slot);return &link;
}
int main(void) {
    int32_t ch[16]={10000,-10000,-10000,0,10000,5000,-5000};
    assert(tx15_rf_rc_select(-1,0));tx15_rf_rc_update(ch,7,1,0);tx15_rf_rc_tick(0);assert(!frames);
    assert(!tx15_rf_rc_select(1,0));assert(link.slot==-1);
    assert(tx15_rf_rc_select(0,1));
    tx15_rf_rc_update(ch,7,1,1);tx15_rf_rc_tick(1);
    assert(frames==1 && crsf_frame_valid(&frame));
    assert(ticks(0)==1792 && ticks(1)==192 && ticks(2)==192);
#ifdef TX15_ELRS_PRODUCT
    assert(ticks(4)==1792 && ticks(13)==992);
#else
    assert(ticks(4)==192 && ticks(13)==192);
#endif
    for(now=2;now<99;now++)tx15_rf_rc_tick(now);
    assert(frames==25);
    tx15_rf_rc_update(ch,7,0,99);tx15_rf_rc_tick(101);assert(frames==25);
    assert(tx15_rf_rc_report.stale==1);
    tx15_rf_rc_update(ch,17,1,102);tx15_rf_rc_tick(102);assert(frames==25);
    assert(tx15_rf_rc_select(-1,103));tx15_rf_rc_tick(104);assert(frames==25 && !tx15_rf_rc_enabled());
    uart_ok=0;assert(!tx15_rf_rc_select(0,105));assert(!tx15_rf_rc_enabled() && stops);
}
