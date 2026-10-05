#ifdef TX15_ELRS_RC
#ifdef TX15_ELRS_PRODUCT
#include "rf_product.inc"
#else
#include "rf_rc.h"
#include "rf_lua.h"
#include "../../../../../hardware/tx15/board/rf_uart.h"
static struct crsf_rc rc;
volatile struct crsf_rc_report tx15_rf_rc_report;
#ifdef TX15_RC_TEST
static uint32_t lock(void) {return 0;}
static void unlock(uint32_t old) {(void)old;}
#else
static uint32_t lock(void) {
    uint32_t old;__asm volatile("mrs %0,primask\ncpsid i":"=r"(old)::"memory");return old;
}
static void unlock(uint32_t old) {__asm volatile("msr primask,%0"::"r"(old):"memory");}
#endif
static int send(void *ctx,const uint8_t *data,unsigned size) {
    (void)ctx;return tx15_rf_uart_send(data,size);
}
int tx15_rf_rc_select(int slot,uint32_t now) {
    uint32_t old=lock();crsf_rc_select(&rc,-1,now);tx15_rf_rc_report=rc.report;unlock(old);
    /* Disable periodic publishing before stopping/reinitializing the UART.
     * All router operations remain main-task only. External fails closed. */
    struct crsf_link *link=tx15_rf_lua_select(slot==0?0:-1);
    if(slot!=0)return slot==-1;
    if(link->slot!=0)return 0;
    old=lock();crsf_rc_select(&rc,0,now);tx15_rf_rc_report=rc.report;unlock(old);return 1;
}
int tx15_rf_rc_enabled(void) {return rc.report.active;}
void tx15_rf_rc_update(const int32_t *ch,unsigned count,int analog_ok,uint32_t now) {
    if(!analog_ok || !ch || count<5 || count>16 || !rc.report.active)return;
    int32_t safe[16]={0};
    for(unsigned i=0;i<count;i++)safe[i]=ch[i];
#ifndef TX15_ELRS_PRODUCT
    safe[4]=safe[13]=-10000; /* Retain explicit restrictions in RAM benches. */
#endif
    /* Encode outside the critical section; publish only a complete frame. */
    struct crsf_rc packed;crsf_rc_init(&packed);crsf_rc_select(&packed,0,now);
    crsf_rc_publish(&packed,safe,16,now);
    uint32_t old=lock();
    if(rc.report.active) {
        rc.frame=packed.frame;rc.report.sample_ms=now;rc.report.published++;rc.fresh=1;
    }
    tx15_rf_rc_report=rc.report;unlock(old);
}
void tx15_rf_rc_tick(uint32_t now) {
    crsf_rc_tick(&rc,now,send,0);tx15_rf_rc_report=rc.report;
}
int tx15_rf_rc_tools_ready(uint32_t now) {return crsf_rc_tools_ready(&rc,now);}
int tx15_rf_rc_send_tool(const uint8_t *data,unsigned size,uint32_t now) {
    uint32_t old=lock();
    int accepted=crsf_rc_tools_ready(&rc,now) && tx15_rf_uart_send(data,size);
    unlock(old);return accepted;
}
#endif

#endif
