#include <assert.h>
#include <string.h>
#include "target/tx/radiomaster/tx15/rf.h"
#include "target/tx/radiomaster/tx15/rf_lua.h"
#include "hardware/tx15/board/rf_uart.h"
volatile struct tx15_rf_report tx15_rf_report;
volatile struct tx15_rf_uart_stats tx15_rf_uart_stats;
static unsigned sent,stopped,read_at,size;
static int init_ok=1,busy;
static uint8_t bytes[64];
uint32_t CLOCK_getms(void) { return 1000; }
int tx15_rf_uart_init(void) {return init_ok;}
void tx15_rf_uart_stop(void) {stopped++;}
int tx15_rf_uart_read(uint8_t *b) {if(read_at==size)return 0;*b=bytes[read_at++];return 1;}
int tx15_rf_uart_send(const uint8_t *data,unsigned length)
{
    if(busy) return 0;
    assert(length==6 || length==8);assert(data[2]==0x28 || data[2]==0x2c);sent++;return 1;
}
int main(void)
{
    init_ok=0;struct crsf_link *link=tx15_rf_lua_init();assert(link->slot==-1 && tx15_rf_report.state==4);
    tx15_rf_lua_poll();assert(!sent);init_ok=1;link=tx15_rf_lua_init();assert(link->slot==0);
    uint8_t ping[]={0,0xea};assert(crsf_link_push(link,0x28,ping,2));busy=1;tx15_rf_lua_poll();
    assert(!sent && link->tx_count==1);busy=0;tx15_rf_lua_poll();assert(sent==1 && !link->tx_count);
    uint8_t reply[]={0xea,0xee,1,0,0,11,'F',0};struct crsf_frame frame;
    assert(crsf_frame_build(&frame,0xea,0x2b,reply,sizeof(reply)));
    memcpy(bytes,frame.bytes,frame.size);size=frame.size;read_at=0;tx15_rf_lua_poll();
    struct crsf_message m;assert(crsf_link_pop(link,&m) && m.type==0x2b && m.size==sizeof(reply));
    assert(!memcmp(m.payload,reply,m.size));
    uint8_t write[]={0xee,0xea,1,1};assert(crsf_link_push(link,0x2d,write,4));tx15_rf_lua_poll();assert(sent==1);
    uint32_t gen=link->generation;tx15_rf_lua_stop();assert(stopped==1 && link->slot==-1 && gen!=link->generation);
    assert(link->tx_count==0 && link->rx_count==0);tx15_rf_lua_stop();assert(stopped==1);
    tx15_rf_lua_poll();assert(sent==1);
}
