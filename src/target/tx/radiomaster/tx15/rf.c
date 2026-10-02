/* Opt-in read-only module discovery; GPL-3.0-or-later.
 * Sends ONLY a device ping (0x28). No RC, bind, configuration or model ID.
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
static int send_ping(void *context,int slot,uint32_t generation,const uint8_t *data,unsigned size)
{
    (void)context;
    if (slot!=CRSF_SLOT_INTERNAL || generation!=link.generation || size!=6 || data[2]!=0x28) return 0;
    return tx15_rf_uart_send(data,size);
}
void tx15_rf_discovery_init(uint32_t now)
{
    tx15_rf_report=(struct tx15_rf_report){0};
    crsf_link_init(&link);memset(&stream,0,sizeof(stream));
    previous_errors=previous_dropped=0;started=last_ping=now;
    if (!tx15_rf_uart_init()) {tx15_rf_report.state=4;return;}
    crsf_link_select(&link,CRSF_SLOT_INTERNAL);
    tx15_rf_report.state=1;
}
void tx15_rf_discovery_poll(uint32_t now)
{
    if (tx15_rf_report.state!=1) return;
    tx15_rf_report.rx_bytes=tx15_rf_uart_stats.rx_bytes;
    tx15_rf_report.tx_bytes=tx15_rf_uart_stats.tx_bytes;
    tx15_rf_report.errors=tx15_rf_uart_stats.errors;
    tx15_rf_report.dropped=tx15_rf_uart_stats.rx_dropped;
    if (previous_errors!=tx15_rf_report.errors || previous_dropped!=tx15_rf_report.dropped) {
        stream.size=0;previous_errors=tx15_rf_report.errors;previous_dropped=tx15_rf_report.dropped;
    }
    uint8_t byte;struct crsf_frame frame;
    for (unsigned n=0;n<256 && tx15_rf_uart_read(&byte);n++) {
        if (crsf_stream_feed(&stream,byte,now,&frame)) {
            tx15_rf_report.frames++;
            struct crsf_device device;
            if (crsf_link_receive(&link,CRSF_SLOT_INTERNAL,link.generation,&frame)
                && crsf_device_info(&frame,&device)) {
                tx15_rf_report.device=device;
                tx15_rf_uart_stop();crsf_link_select(&link,CRSF_SLOT_OFF);
                tx15_rf_report.state=2;return;
            }
            struct crsf_message discard;
            while (crsf_link_pop(&link,&discard)) {}
        }
    }
    if ((uint32_t)(now-started)>=15000) {
        tx15_rf_uart_stop();crsf_link_select(&link,CRSF_SLOT_OFF);
        tx15_rf_report.state=3;return;
    }
    if ((uint32_t)(now-last_ping)>=1000) {
        const uint8_t ping[]={0,0xea};
        if (crsf_link_push(&link,0x28,ping,sizeof(ping))) {last_ping=now;tx15_rf_report.pings++;}
    }
    crsf_link_service(&link,send_ping,0);
}
