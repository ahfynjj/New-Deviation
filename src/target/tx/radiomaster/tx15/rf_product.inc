/* Dual native module sessions. Main owns configuration; SysTick sends RC. */
#include "rf_rc.h"
#include "rf_lua.h"
#include "../../../../../hardware/tx15/board/rf_external.h"
static struct crsf_rc modules[2];
volatile struct crsf_rc_report tx15_rf_rc_report,tx15_rf_module_reports[2];
#ifdef TX15_RC_TEST
static uint32_t lock(void) {return 0;}static void unlock(uint32_t old) {(void)old;}
#else
static uint32_t lock(void) {uint32_t old;__asm volatile("mrs %0,primask\ncpsid i":"=r"(old)::"memory");return old;}
static void unlock(uint32_t old) {__asm volatile("msr primask,%0"::"r"(old):"memory");}
#endif
static void report(unsigned slot) {
 tx15_rf_module_reports[slot]=modules[slot].report;
 if(!slot)tx15_rf_rc_report=modules[0].report;
}
static int send(void *ctx,const uint8_t *data,unsigned n) {
 return (uintptr_t)ctx ? tx15_rf_external_send(data,n) : tx15_rf_uart_send(data,n);
}
int tx15_rf_module_active(unsigned slot) {return slot<2 && modules[slot].report.active;}
int tx15_rf_module_enable(unsigned slot,int on,uint32_t now) {
 if(slot>1)return 0;
 if(tx15_rf_module_active(slot)==!!on)return 1;
 uint32_t old=lock();crsf_rc_select(&modules[slot],-1,now);report(slot);unlock(old);
 if(tx15_rf_tools_slot()==(int)slot)tx15_rf_lua_shutdown();
 if(slot)tx15_rf_external_stop();else tx15_rf_uart_stop();
 if(!on)return 1;
 int ok=slot ? tx15_rf_external_init() : tx15_rf_uart_init();
 if(!ok)return 0;
 old=lock();crsf_rc_select(&modules[slot],0,now);report(slot);unlock(old);return 1;
}
int tx15_rf_rc_select(int slot,uint32_t now) {
 if(slot!=0 && slot!=-1)return 0;
 int ok=tx15_rf_module_enable(0,slot==0,now);
 if(ok && slot==0)tx15_rf_lua_select(0);
 return ok;
}
int tx15_rf_rc_enabled(void) {return tx15_rf_module_active(0);}
void tx15_rf_module_update(unsigned slot,const int32_t *ch,unsigned count,int ok,uint32_t now) {
 if(slot>1 || !ok || !ch || count<5 || count>16 || !tx15_rf_module_active(slot))return;
 int32_t values[16]={0};for(unsigned i=0;i<count;i++)values[i]=ch[i];
 struct crsf_rc packed;crsf_rc_init(&packed);crsf_rc_select(&packed,0,now);
 crsf_rc_publish(&packed,values,16,now);
 uint32_t old=lock();
 if(modules[slot].report.active) {
  modules[slot].frame=packed.frame;modules[slot].report.sample_ms=now;
  modules[slot].report.published++;modules[slot].fresh=1;
 }report(slot);unlock(old);
}
void tx15_rf_rc_update(const int32_t *ch,unsigned count,int ok,uint32_t now) {tx15_rf_module_update(0,ch,count,ok,now);}
void tx15_rf_rc_tick(uint32_t now) {
 for(unsigned slot=0;slot<2;slot++) {crsf_rc_tick(&modules[slot],now,send,(void *)(uintptr_t)slot);report(slot);}
}
int tx15_rf_rc_tools_ready(uint32_t now) {
 int slot=tx15_rf_tools_slot();return slot>=0 && slot<2 && tx15_rf_module_active(slot) && crsf_rc_tools_ready(&modules[slot],now);
}
int tx15_rf_rc_send_tool(const uint8_t *data,unsigned size,uint32_t now) {
 uint32_t old=lock();int slot=tx15_rf_tools_slot();
 int accepted=tx15_rf_rc_tools_ready(now) && send((void *)(uintptr_t)slot,data,size);
 unlock(old);return accepted;
}
