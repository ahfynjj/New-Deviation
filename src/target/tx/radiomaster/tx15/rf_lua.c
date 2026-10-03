/* Internal CRSF tool session; GPL-3.0-or-later. No RC or writes in first bench. */
#ifdef TX15_ELRS_LUA
#include <string.h>
#include "rf.h"
#include "rf_lua.h"
#include "../../../../../hardware/tx15/board/rf_uart.h"
static struct crsf_link lua_link;
static struct crsf_stream lua_stream;
static uint32_t errors,dropped;
static unsigned active;
extern uint32_t CLOCK_getms(void);
struct crsf_link *tx15_rf_lua_init(void)
{
    tx15_rf_lua_stop();
    crsf_link_init(&lua_link);memset(&lua_stream,0,sizeof(lua_stream));
    tx15_rf_report=(struct tx15_rf_report){0};errors=dropped=0;
    active=tx15_rf_uart_init();
    if(active) {crsf_link_select(&lua_link,CRSF_SLOT_INTERNAL);tx15_rf_report.state=7;}
    else tx15_rf_report.state=4;
    return &lua_link;
}
void tx15_rf_lua_stop(void)
{
    if(!active) return;
    tx15_rf_uart_stop();crsf_link_select(&lua_link,CRSF_SLOT_OFF);active=0;
    tx15_rf_report.state=2;
}
static int send(void *ctx,int slot,uint32_t generation,const uint8_t *data,unsigned size)
{
    (void)ctx;
    if(slot!=0 || generation!=lua_link.generation) return 0;
    /* Defense in depth below the interpreter. No queued write/RC can escape. */
    if(!((size==6 && data[2]==0x28 && data[3]==0 && data[4]==0xea)
      || (size==8 && data[2]==0x2c && data[3]==0xee && data[4]==0xea))) return 0;
    if(!tx15_rf_uart_send(data,size)) return 0;
    if(data[2]==0x28) tx15_rf_report.pings++;else tx15_rf_report.requests++;
    return 1;
}
void tx15_rf_lua_poll(void)
{
    if(!active) return;
    tx15_rf_report.rx_bytes=tx15_rf_uart_stats.rx_bytes;tx15_rf_report.tx_bytes=tx15_rf_uart_stats.tx_bytes;
    tx15_rf_report.errors=tx15_rf_uart_stats.errors;tx15_rf_report.dropped=tx15_rf_uart_stats.rx_dropped;
    if(errors!=tx15_rf_report.errors || dropped!=tx15_rf_report.dropped) {
        lua_stream.size=0;errors=tx15_rf_report.errors;dropped=tx15_rf_report.dropped;
    }
    uint8_t byte;struct crsf_frame frame;
    for(unsigned n=0;n<256 && tx15_rf_uart_read(&byte);n++) {
        if(!crsf_stream_feed(&lua_stream,byte,CLOCK_getms(),&frame)) continue;
        tx15_rf_report.frames++;
        if(!crsf_link_receive(&lua_link,0,lua_link.generation,&frame)) continue;
        struct crsf_device device;
        if(crsf_device_info(&frame,&device)) tx15_rf_report.device=device;
    }
    crsf_link_service(&lua_link,send,NULL);
}
#endif
