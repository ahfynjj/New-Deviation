#include <assert.h>
#include <string.h>
#include "target/tx/radiomaster/tx15/rf.h"
#include "target/tx/radiomaster/tx15/rf_lua.h"
#include "target/tx/radiomaster/tx15/rf_rc.h"
#include "hardware/tx15/board/rf_uart.h"
volatile struct tx15_rf_report tx15_rf_report;
volatile struct tx15_rf_uart_stats tx15_rf_uart_stats;
static uint32_t now=1000;
static unsigned stopped,rc_frames,tools_frames;
uint32_t CLOCK_getms(void) {return now;}
int tx15_rf_uart_init(void) {return 1;}
void tx15_rf_uart_stop(void) {stopped++;}
int tx15_rf_uart_read(uint8_t *b) {(void)b;return 0;}
int tx15_rf_uart_send(const uint8_t *data,unsigned size) {
    (void)size;if(data[2]==0x16)rc_frames++;else tools_frames++;return 1;
}
int main(void) {
    struct crsf_link *link=tx15_rf_lua_init();assert(link->slot==-1 && !stopped);
    assert(tx15_rf_rc_select(0,now));link=tx15_rf_lua_init();assert(link->slot==0);
    int32_t ch[7]={0,0,-10000,0,-10000,0,0};
    tx15_rf_rc_update(ch,7,1,now);tx15_rf_rc_tick(now);assert(rc_frames==1);
    uint8_t ping[]={0,0xea};assert(crsf_link_push(link,0x28,ping,2));
    now+=2;tx15_rf_lua_poll();assert(tools_frames==0 && link->tx_count==1);
    now+=2;tx15_rf_rc_tick(now);now++;tx15_rf_lua_poll();assert(tools_frames==1);
    assert(crsf_link_push(link,0x28,ping,2));uint32_t generation=link->generation;
    tx15_rf_lua_stop(); /* Script failure/close: discard tool queues, keep RC. */
    assert(!stopped && !link->tx_count && generation!=link->generation);
    now+=3;tx15_rf_rc_tick(now);assert(rc_frames==3);
    assert(tx15_rf_rc_select(-1,now));assert(stopped==1 && link->slot==-1);
    now+=4;tx15_rf_rc_tick(now);assert(rc_frames==3);
}
