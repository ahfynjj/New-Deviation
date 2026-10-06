#include <assert.h>
#include <string.h>
#include "target/tx/radiomaster/tx15/rf.h"
#include "target/tx/radiomaster/tx15/rf_lua.h"
#include "target/tx/radiomaster/tx15/rf_rc.h"
#include "hardware/tx15/board/rf_external.h"
#include "hardware/tx15/board/status.h"
extern struct tx15_link_status tx15_link_status[2];
static struct crsf_frame incoming[2];static unsigned pos[2];
static int read_byte(unsigned slot,uint8_t *p) {if(pos[slot]>=incoming[slot].size)return 0;*p=incoming[slot].bytes[pos[slot]++];return 1;}
volatile struct tx15_rf_report tx15_rf_report;
volatile struct tx15_rf_uart_stats tx15_rf_uart_stats,tx15_rf_external_stats;
static uint32_t now=1000;static unsigned frames[2],tools[2],stops[2];
static struct crsf_frame rcframe[2];
uint32_t CLOCK_getms(void) {return now;}
int tx15_rf_uart_init(void) {return 1;}int tx15_rf_external_init(void) {return 1;}
void tx15_rf_uart_stop(void) {stops[0]++;}void tx15_rf_external_stop(void) {stops[1]++;}
int tx15_rf_uart_read(uint8_t *p) {return read_byte(0,p);}int tx15_rf_external_read(uint8_t *p) {return read_byte(1,p);}
static int send(unsigned slot,const uint8_t *p,unsigned n) {
 if(p[2]==0x16){frames[slot]++;memcpy(rcframe[slot].bytes,p,n);rcframe[slot].size=n;}else tools[slot]++;return 1;
}
int tx15_rf_uart_send(const uint8_t *p,unsigned n) {return send(0,p,n);}
int tx15_rf_external_send(const uint8_t *p,unsigned n) {return send(1,p,n);}
int main(void) {
 assert(tx15_rf_module_enable(0,1,now));assert(tx15_rf_module_enable(1,1,now));
 int32_t ch[16]={10000,-10000,-10000,0,10000};
 tx15_rf_module_update(0,ch,16,1,now);tx15_rf_module_update(1,ch,16,1,now);tx15_rf_rc_tick(now);
 assert(frames[0]==1 && frames[1]==1);
 unsigned bit=4*11;unsigned word=rcframe[0].bytes[3+bit/8]|(rcframe[0].bytes[4+bit/8]<<8)|(rcframe[0].bytes[5+bit/8]<<16);
 assert(((word>>(bit%8))&2047)==1792);
 struct crsf_link *link=tx15_rf_lua_select(1);assert(link->slot==1);uint32_t generation=link->generation;
 uint8_t ping[]={0,0xea};assert(crsf_link_push(link,0x28,ping,2));now++;tx15_rf_lua_poll();
 assert(tools[1]==1 && !tools[0]);
 link=tx15_rf_lua_select(0);assert(link->slot==0 && link->generation!=generation && !link->tx_count);
 unsigned before0=stops[0],before1=stops[1];
 tx15_rf_lua_stop();assert(tx15_rf_module_active(0) && tx15_rf_module_active(1) && stops[0]==before0 && stops[1]==before1);
 unsigned char stats[10]={70,80,95,0,0,0,0,0,0,0};
 assert(crsf_frame_build(&incoming[0],0xea,0x14,stats,10));
 stats[0]=90;stats[2]=55;assert(crsf_frame_build(&incoming[1],0xea,0x14,stats,10));
 tx15_rf_lua_poll();assert(tx15_rf_tools_slot()==-1);
 assert(tx15_link_status[0].rssi_dbm==-70 && tx15_link_status[0].lq==95);
 assert(tx15_link_status[1].rssi_dbm==-90 && tx15_link_status[1].lq==55);
 now+=3;tx15_rf_rc_tick(now);assert(frames[0]==2 && frames[1]==2);
 assert(tx15_rf_module_enable(0,0,now));assert(!tx15_rf_module_active(0) && tx15_rf_module_active(1));
 assert(tx15_rf_lua_select(0)->slot==-1);
 assert(tx15_rf_lua_select(1)->slot==1);
 assert(tx15_rf_module_enable(1,0,now));assert(!tx15_rf_module_active(1));
 tx15_rf_lua_poll();assert(tx15_rf_tools_slot()==-1);
 assert(!tx15_link_status[0].valid && !tx15_link_status[1].valid);
}
