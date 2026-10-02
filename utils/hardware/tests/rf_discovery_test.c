#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "target/tx/radiomaster/tx15/rf.h"
#include "hardware/tx15/board/rf_uart.h"
volatile struct tx15_rf_uart_stats tx15_rf_uart_stats;
static int init_ok=1,stopped;
static unsigned sent,at,available;
static uint8_t received[64];
int tx15_rf_uart_init(void) {return init_ok;}
void tx15_rf_uart_stop(void) {stopped++;}
int tx15_rf_uart_read(uint8_t *byte) {
    if(at==available)return 0;
    *byte=received[at++];return 1;
}
int tx15_rf_uart_send(const uint8_t *p,unsigned size) {
    assert(size==6 && p[0]==0xee && p[2]==0x28 && p[3]==0 && p[4]==0xea);
    sent++;return 1;
}
int main(void) {
    init_ok=0;tx15_rf_discovery_init(0);assert(tx15_rf_report.state==4);
    tx15_rf_discovery_poll(10000);assert(!sent);
    init_ok=1;tx15_rf_discovery_init(0);
    for(unsigned ms=0;ms<=15000;ms++)tx15_rf_discovery_poll(ms);
    assert(tx15_rf_report.state==3 && stopped==1 && sent==14);
    tx15_rf_discovery_poll(16000);assert(sent==14);
    tx15_rf_discovery_init(20000);tx15_rf_discovery_poll(21000);
    uint8_t data[]={0xea,0xee,'E','L','R','S',0,0x45,0x4c,0x52,0x53,0,0,0,1,0,0,0,2,9,0};
    struct crsf_frame frame;
    assert(crsf_frame_build(&frame,0xea,0x29,data,sizeof(data)));
    memcpy(received,frame.bytes,frame.size);available=frame.size;
    tx15_rf_discovery_poll(21005);
    assert(tx15_rf_report.state==2 && stopped==2);
    assert(!strcmp((const char *)tx15_rf_report.device.name,"ELRS"));
    assert(tx15_rf_report.device.serial==0x454c5253 && tx15_rf_report.device.fields==9);
    assert(sent==15);tx15_rf_discovery_poll(90000);assert(sent==15);
    puts("Discovery sends only ping, decodes response, powers off on completion/timeout PASS");
}
