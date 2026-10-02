/* Opt-in read-only module discovery; GPL-3.0-or-later.
 * Sends device ping (0x28) and optional parameter READ (0x2c).
 * No RC, bind, configuration writes or model ID.
 * Module power is enabled while waiting, then disabled on success/timeout.
 * This is not the flight UART scheduler or a protocol selection implementation.
 */
#include "rf.h"
#include "../../../../../hardware/tx15/board/rf_uart.h"
#include <string.h>
static struct crsf_link link;
static struct crsf_stream stream;
static uint32_t started,last_ping,previous_errors,previous_dropped;
volatile struct tx15_rf_report tx15_rf_report;
struct crsf_params tx15_rf_parameters;
#ifdef TX15_ELRS_PARAMETERS
static uint32_t request_time,service_now,error_baseline,drop_baseline;
static unsigned pending,inflight,attempts;
#endif
static void finish(unsigned state)
{
    tx15_rf_uart_stop();crsf_link_select(&link,CRSF_SLOT_OFF);
    tx15_rf_report.state=state;
}
static int send_ping(void *context,int slot,uint32_t generation,const uint8_t *data,unsigned size)
{
    (void)context;
    if (slot!=CRSF_SLOT_INTERNAL || generation!=link.generation || size<6) return 0;
    int allowed=size==6 && data[2]==0x28 && data[3]==0 && data[4]==0xea;
#ifdef TX15_ELRS_PARAMETERS
    allowed|=size==8 && data[2]==0x2c && data[3]==0xee && data[4]==0xea;
#endif
    if (!allowed || !tx15_rf_uart_send(data,size)) return 0;
#ifdef TX15_ELRS_PARAMETERS
    if (data[2]==0x2c) {request_time=service_now;inflight=1;tx15_rf_report.requests++;}
#endif
    return 1;
}
void tx15_rf_discovery_init(uint32_t now)
{
    tx15_rf_report=(struct tx15_rf_report){0};
    crsf_link_init(&link);memset(&stream,0,sizeof(stream));
    previous_errors=previous_dropped=0;started=last_ping=now;
#ifdef TX15_ELRS_PARAMETERS
    pending=inflight=attempts=0;error_baseline=drop_baseline=0;
#endif
    if (!tx15_rf_uart_init()) {tx15_rf_report.state=4;return;}
    crsf_link_select(&link,CRSF_SLOT_INTERNAL);
    tx15_rf_report.state=1;
}
void tx15_rf_discovery_poll(uint32_t now)
{
    if (tx15_rf_report.state!=1 && tx15_rf_report.state!=5) return;
    tx15_rf_report.rx_bytes=tx15_rf_uart_stats.rx_bytes;
    tx15_rf_report.tx_bytes=tx15_rf_uart_stats.tx_bytes;
    tx15_rf_report.errors=tx15_rf_uart_stats.errors;
    tx15_rf_report.dropped=tx15_rf_uart_stats.rx_dropped;
#ifdef TX15_ELRS_PARAMETERS
    service_now=now;
    if (tx15_rf_report.state==5) {
        tx15_rf_report.active_errors=tx15_rf_report.errors-error_baseline;
        tx15_rf_report.active_dropped=tx15_rf_report.dropped-drop_baseline;
    }
#endif
    if (previous_errors!=tx15_rf_report.errors || previous_dropped!=tx15_rf_report.dropped) {
        stream.size=0;previous_errors=tx15_rf_report.errors;previous_dropped=tx15_rf_report.dropped;
    }
    uint8_t byte;struct crsf_frame frame;
    for (unsigned n=0;n<256 && tx15_rf_uart_read(&byte);n++) {
        if (crsf_stream_feed(&stream,byte,now,&frame)) {
            tx15_rf_report.frames++;
            struct crsf_device device;
            int accepted=crsf_link_receive(&link,CRSF_SLOT_INTERNAL,link.generation,&frame);
            if (tx15_rf_report.state==1 && accepted
                && crsf_device_info(&frame,&device)) {
                tx15_rf_report.device=device;
#ifdef TX15_ELRS_PARAMETERS
                if (!crsf_params_init(&tx15_rf_parameters,device.fields)) {finish(6);return;}
                if (!device.fields) {finish(2);return;}
                error_baseline=tx15_rf_report.errors;drop_baseline=tx15_rf_report.dropped;
                tx15_rf_report.state=5;
#else
                finish(2);return;
#endif
            }
            struct crsf_message discard;
            while (crsf_link_pop(&link,&discard)) {
#ifdef TX15_ELRS_PARAMETERS
                if (tx15_rf_report.state==5 && inflight) {
                    int result=crsf_params_accept(&tx15_rf_parameters,&discard);
                    if (result<0) {tx15_rf_report.failed_id=tx15_rf_parameters.current;finish(6);return;}
                    if (result>0) {
                        pending=inflight=attempts=0;
                        tx15_rf_report.completed=tx15_rf_parameters.current-1;
                        if (result==3) {finish(2);return;}
                    }
                }
#endif
            }
        }
    }
    if ((uint32_t)(now-started)>=(tx15_rf_report.state==5?45000u:15000u)) {
        finish(3);return;
    }
    if (tx15_rf_report.state==1 && (uint32_t)(now-last_ping)>=1000) {
        const uint8_t ping[]={0,0xea};
        if (crsf_link_push(&link,0x28,ping,sizeof(ping))) {last_ping=now;tx15_rf_report.pings++;}
    }
#ifdef TX15_ELRS_PARAMETERS
    if (tx15_rf_report.state==5) {
        if (inflight && (uint32_t)(now-request_time)>=500) {
            if (++attempts>=3) {tx15_rf_report.failed_id=tx15_rf_parameters.current;finish(3);return;}
            pending=inflight=0;tx15_rf_report.retries++;
        }
        if (!pending) {
            uint8_t request[4];
            if (crsf_params_request(&tx15_rf_parameters,request) && crsf_link_push(&link,0x2c,request,4)) pending=1;
        }
    }
#endif
    crsf_link_service(&link,send_ping,0);
}
