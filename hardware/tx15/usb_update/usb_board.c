/* Native CDC board glue, no HAL/RTOS or Flash writer; GPL-3.0-or-later. */
#include "usb_board.h"
#include "usb_hw.h"
#include "tusb.h"
#include "device/dcd.h"
#include "stm32h7xx.h"
uint32_t SystemCoreClock=128000000u;
static volatile uint32_t ticks,epoch;
static unsigned started,attached;
static uint32_t last_sync;
static int sync_seen;
void SysTick_Handler(void) { ticks++; }
uint32_t board_millis(void) { return ticks; }
uint32_t tx15_usb_ms(void) { return ticks; }
void OTG_FS_IRQHandler(void) { tusb_int_handler(0,true); }
void tud_event_hook_cb(uint8_t rhport,uint32_t event,bool in_isr)
{
    (void)rhport;(void)in_isr;
    if (event==DCD_EVENT_BUS_RESET || event==DCD_EVENT_UNPLUGGED) epoch++;
}
int tx15_usb_init(void)
{
    if (tx15_usb_hw_init(1000000u)) return -1;
    SysTick->CTRL=0;SysTick->LOAD=127999u;SysTick->VAL=0;
    NVIC_SetPriority(SysTick_IRQn,15);
    NVIC_SetPriority(OTG_FS_IRQn,8);
    /* PA9 has no VBUS input on TX15. Use the separate PH5 detector and
     * software connect gating; H750 B-session override is needed for FS. */
    USB2_OTG_FS->GCCFG &= ~USB_OTG_GCCFG_VBDEN;
    USB2_OTG_FS->GOTGCTL |= USB_OTG_GOTGCTL_BVALOEN|USB_OTG_GOTGCTL_BVALOVAL;
    tusb_rhport_init_t init={.role=TUSB_ROLE_DEVICE,.speed=TUSB_SPEED_FULL};
    if (!tusb_init(0,&init)) return -2;
    tud_disconnect();attached=0;started=1;sync_seen=0;epoch++;
    SysTick->CTRL=7;
    return 0;
}
void tx15_usb_poll(void)
{
    if (!started) return;
    int vbus=tx15_usb_hw_vbus();
    if ((unsigned)vbus!=attached) {
        attached=(unsigned)vbus;epoch++;sync_seen=0;
        if (vbus) tud_connect();else tud_disconnect();
    }
    tud_task();
    int sync=tx15_usb_hw_sync();
    if (sync>0) { last_sync=ticks;sync_seen=1; }
    else if (sync<0) sync_seen=0;
}
int tx15_usb_connected(void) { return started && attached && tud_mounted(); }
int tx15_usb_synchronized(void)
{ return tx15_usb_connected() && sync_seen && (uint32_t)(ticks-last_sync)<1000u; }
uint32_t tx15_usb_epoch(void) { return epoch; }
int tx15_usb_new_session(uint64_t *session) { return tx15_usb_hw_session(session,1000000u); }
size_t tx15_usb_read(uint8_t *p,size_t n)
{ return tx15_usb_connected()?tud_cdc_read(p,(uint32_t)n):0; }
size_t tx15_usb_write(const uint8_t *p,size_t n)
{
    if (!tx15_usb_connected()) return 0;
    uint32_t sent=tud_cdc_write(p,(uint32_t)n);tud_cdc_write_flush();return sent;
}
void tx15_usb_stop(void)
{
    if (started) { tud_disconnect();tud_deinit(0); }
    NVIC_DisableIRQ(OTG_FS_IRQn);NVIC_ClearPendingIRQ(OTG_FS_IRQn);
    SysTick->CTRL=0;SCB->ICSR=SCB_ICSR_PENDSTCLR_Msk;
    started=0;attached=0;sync_seen=0;epoch++;
}
