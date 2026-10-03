/* Internal CRSF Lua session; GPL-3.0-or-later. No RC; selection writes opt-in. */
#ifdef TX15_ELRS_LUA
#include <string.h>
#include "rf.h"
#include "rf_lua.h"
#ifdef TX15_ELRS_RC
#include "rf_rc.h"
#endif
#include "protocol/transport/crsf_tools.h"
#include "../../../../../hardware/tx15/board/rf_uart.h"
static struct crsf_link lua_link={.slot=CRSF_SLOT_OFF};
static struct crsf_stream lua_stream;
static struct crsf_tools tools;
volatile struct crsf_tool_report tx15_rf_write_report;
static uint32_t errors,dropped;
static unsigned active;
extern uint32_t CLOCK_getms(void);
struct crsf_link *tx15_rf_lua_select(int slot)
{
    tx15_rf_lua_shutdown();
    crsf_link_init(&lua_link);memset(&lua_stream,0,sizeof(lua_stream));
#ifdef TX15_ELRS_WRITE
    crsf_tools_init(&tools,1);
#else
    crsf_tools_init(&tools,0);
#endif
    tx15_rf_write_report=tools.report;
    tx15_rf_report=(struct tx15_rf_report){0};errors=dropped=0;
    if(slot!=CRSF_SLOT_INTERNAL)return &lua_link;
    active=tx15_rf_uart_init();
    if(active) {crsf_link_select(&lua_link,CRSF_SLOT_INTERNAL);tx15_rf_report.state=7;}
    else tx15_rf_report.state=4;
    return &lua_link;
}
struct crsf_link *tx15_rf_lua_init(void)
{
#ifdef TX15_ELRS_RC
    return &lua_link; /* Model owns the session; opening Lua never powers RF. */
#else
    return tx15_rf_lua_select(CRSF_SLOT_INTERNAL);
#endif
}
void tx15_rf_lua_shutdown(void)
{
    if(!active) return;
    tx15_rf_uart_stop();crsf_link_select(&lua_link,CRSF_SLOT_OFF);active=0;
    crsf_tools_cancel(&tools);tx15_rf_write_report=tools.report;
    tx15_rf_report.state=2;
}
void tx15_rf_lua_stop(void)
{
#ifdef TX15_ELRS_RC
    if(tx15_rf_rc_enabled()) {
        crsf_tools_cancel(&tools);tx15_rf_write_report=tools.report;
        crsf_link_select(&lua_link,CRSF_SLOT_INTERNAL);lua_stream.size=0;return;
    }
#endif
    tx15_rf_lua_shutdown();
}
static int send(void *ctx,int slot,uint32_t generation,const uint8_t *data,unsigned size)
{
    (void)ctx;
    if(slot!=0 || generation!=lua_link.generation) return 0;
    int kind=size>=6?crsf_tools_kind(&tools,data[2],data+3,size-4):0;
    /* Reject permanently forbidden frames without blocking subsequent reads.
     * Busy still returns zero and retains an otherwise authorized frame. */
    if(!kind) {tools.report.denied++;tx15_rf_write_report=tools.report;return 1;}
    if(crsf_tools_defer(&tools,data[2],data+3,size-4,CLOCK_getms()))return 0;
#ifdef TX15_ELRS_RC
    /* Only SysTick publishes RC. Router queues stay in the main task. */
    if(!tx15_rf_rc_send_tool(data,size,CLOCK_getms()))return 0;
#else
    if(!tx15_rf_uart_send(data,size)) return 0;
#endif
    crsf_tools_sent(&tools,data[2],data+3,size-4,CLOCK_getms());
    tx15_rf_write_report=tools.report;
    if(kind==CRSF_TOOL_PING)tx15_rf_report.pings++;
    else if(kind==CRSF_TOOL_READ)tx15_rf_report.requests++;
    return 1;
}
void tx15_rf_lua_poll(void)
{
    if(!active) return;
    crsf_tools_tick(&tools,CLOCK_getms());
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
        struct crsf_message message={.type=frame.bytes[2],.size=frame.size-4};
        memcpy(message.payload,frame.bytes+3,message.size);
        crsf_tools_receive(&tools,&message,CLOCK_getms());
        struct crsf_device device;
        if(crsf_device_info(&frame,&device)) tx15_rf_report.device=device;
    }
    crsf_link_service(&lua_link,send,NULL);
    tx15_rf_write_report=tools.report;
}
int tx15_rf_lua_authorize(uint8_t type,const uint8_t *data,unsigned size)
{ return active && crsf_tools_kind(&tools,type,data,size)!=0; }
int tx15_rf_lua_writes_enabled(void) {return tools.enabled;}
#endif
