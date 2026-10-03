/* Native application runtime on the already initialized RAM bootstrap. */
#include "common.h"
#include "runtime.h"
#include "boot_contract.h"
#ifdef TX15_STANDALONE
#include "../../../../../hardware/tx15/board/power.h"
#include "../../../../../hardware/tx15/boot/power_button.h"
static struct tx15_power_button power_button;
#endif
#ifdef TX15_ELRS_RC
#include "rf_rc.h"
#endif
#include "../../../../../hardware/tx15/board/inputs.h"
#define REPORT ((volatile uint32_t *)0x2400e000u)
u32 CLOCK_getms(void) { return REPORT[11]; }
void CLOCK_ResetWatchdog(void) {
#ifdef TX15_STANDALONE
    if(tx15_power_button_poll(&power_button,CLOCK_getms(),
        (tx15_power_status()&TX15_BUTTON_PRESSED)!=0)) PWR_Shutdown();
#endif
    /* RAM bootstrap does not start IWDG. Keep sampling/heartbeat alive while
     * original Deviation pages run their own cooperative wait loops. */
    if(tx15_runtime_poll(CLOCK_getms())) REPORT[12]++;
}
u32 ScanButtons(void) {
    static int queued;
    static u32 until, pulse;
    static unsigned phase;
    struct tx15_input_event e=tx15_inputs_take();
    queued+=e.rotation; if(queued>8) queued=8; if(queued<-8) queued=-8;
    u32 now=CLOCK_getms();
    if(phase && (s32)(now-until)>=0) {
        if(phase==1) { pulse=0; phase=2; until=now+100; }
        else phase=0;
    }
    if(!phase && queued) {
        /* CHAN_ButtonMask does not parenthesize its argument internally. */
        pulse=queued>0 ? CHAN_ButtonMask(BUT_DOWN) : CHAN_ButtonMask(BUT_UP);
        queued+=(queued>0)?-1:1; phase=1; until=now+100;
    }
    unsigned raw=tx15_inputs_state();
    return pulse | ((raw&TX15_ENTER)?CHAN_ButtonMask(BUT_ENTER):0)
        | ((raw&TX15_EXIT)?CHAN_ButtonMask(BUT_EXIT):0)
        | ((raw&TX15_PREV)?CHAN_ButtonMask(BUT_LEFT):0)
        | ((raw&TX15_NEXT)?CHAN_ButtonMask(BUT_RIGHT):0);
}
void SysTick_Handler(void) {
    REPORT[11]++; tx15_inputs_tick();
#ifdef TX15_ELRS_RC
    tx15_rf_rc_tick(REPORT[11]);
#endif
}
void App_Fault(void) {
    unsigned ipsr; __asm volatile("mrs %0, ipsr":"=r"(ipsr));
    REPORT[14]=ipsr;REPORT[15]=*(volatile u32 *)0xe000ed28u;
    REPORT[16]=*(volatile u32 *)0xe000ed2cu;REPORT[2]=5;
    __asm volatile("cpsid i"); for(;;) __asm volatile("nop");
}
void tx15_app_main(void);
void App_Main(void) {
    /* A standalone build requires the separate native cold-loader contract;
     * legacy RAM sessions retain V6->V7. No clocks/SDRAM reset at this stage. */
    if(!tx15_app_boot_accept((volatile struct probe_report *)REPORT)) App_Fault();
    tx15_inputs_init();
    *(volatile u32 *)0xe000e010u=0;
    *(volatile u32 *)0xe000e014u=127999;
    *(volatile u32 *)0xe000e018u=0;
    *(volatile u32 *)0xe000ed04u=(1u<<25)|(1u<<27);
    *(volatile u32 *)0xe000e010u=7;
    __asm volatile("dsb\nisb\ncpsie i":::"memory");
    tx15_app_main();
}
