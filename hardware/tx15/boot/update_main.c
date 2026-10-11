/* Native resident USB update loop; GPL-3.0-or-later. */
#include "update_mode.h"
#include "qspi.h"
#include "../board/display.h"
#include "../board/power.h"
#include "../usb_update/usb_board.h"
#include "../usb_update/usb_hw.h"
#include "../usb_update/runtime.h"
#include "../usb_update/nor.h"
#include "../usb_update/screen.h"
#include "../ram_probe/probe.h"
#include <string.h>
#define R(a) (*(volatile uint32_t *)(uintptr_t)(a))
static struct tx15_update_runtime runtime;
static struct tx15_update_nor nor;
static struct tx15_frame_parser parser;
static struct tx15_frame reply;
static uint8_t tx[TX15_FRAME_BYTES_MAX];
static size_t tx_bytes,tx_sent;
static unsigned started,in_request;
static uint32_t epoch=UINT32_MAX;
extern volatile struct probe_report probe_report;
static void pump(void*);
static uint32_t ticks(void *ctx) { (void)ctx;return tx15_usb_ms(); }
unsigned tx15_boot_exit_stable(void)
{
    /* PG3 pull-up. A polling 1ms SysTick before USB owns its interrupt. */
    R(0x580244e0u)|=1u<<6;(void)R(0x580244e0u);
    R(0x58021800u)&=~(3u<<6);
    R(0x5802180cu)=(R(0x5802180cu)&~(3u<<6))|(1u<<6);
    R(0xe000e010u)=0;R(0xe000e014u)=127999;R(0xe000e018u)=0;R(0xe000e010u)=5;
    unsigned stable=1;
    for(unsigned ms=0;ms<30;ms++) {
        if(R(0x58021810u)&8u)stable=0;
        unsigned elapsed=0;
        for(unsigned budget=1000000;budget;budget--)
            if(R(0xe000e010u)&(1u<<16)){elapsed=1;break;}
        if(!elapsed){stable=0;break;}
    }
    if(R(0x58021810u)&8u)stable=0;
    R(0xe000e010u)=0;return stable;
}
static void request(void *ctx,const struct tx15_frame *f)
{
    (void)ctx;
    in_request=1;runtime.synchronized=(unsigned)tx15_usb_synchronized();
    tx15_update_runtime_request(&runtime,f,&reply);in_request=0;
    tx_bytes=tx15_update_frame_encode(&reply,tx,sizeof(tx));tx_sent=0;
}
static void pump(void *ctx)
{
    (void)ctx;if(!started)return;
    tx15_usb_poll();
    if(epoch!=tx15_usb_epoch()) {
        epoch=tx15_usb_epoch();uint64_t session=0;(void)tx15_usb_new_session(&session);
        tx15_update_runtime_session(&runtime,session);
        tx15_update_frame_init(&parser);tx_bytes=tx_sent=0;
    }
    /* No recursive dispatcher calls during COMMIT preparation/HELLO/read.
     * Committed transaction steps can service STATUS between NOR busy polls. */
    if(in_request)return;
    if(!runtime.committed)tx15_update_receiver_tick(&runtime.receiver,tx15_usb_ms());
    if(tx_sent<tx_bytes)tx_sent+=tx15_usb_write(tx+tx_sent,tx_bytes-tx_sent);
    else {
        uint8_t byte;
        for(unsigned i=0;i<2048 && tx_sent>=tx_bytes && tx15_usb_read(&byte,1);i++)
            tx15_update_frame_feed(&parser,&byte,1,request,0);
    }
    if(!runtime.receiver.session && tx15_usb_connected() && !runtime.committed)epoch=UINT32_MAX;
}
void tx15_boot_update_run(uint32_t jedec)
{
    /* Updater disables both RF modules. USB initialization also verifies this. */
    R(0x580244e0u)|=0xau;(void)R(0x580244e0u);
    R(0x58020418u)=1u<<29;R(0x58020c18u)=1u<<20;
    R(0x58020c04u)&=~(1u<<4);
    R(0x58020c00u)=(R(0x58020c00u)&~(3u<<8))|(1u<<8);
    tx15_display_fill(0);
    unsigned display_ok=tx15_display_init()==0;
    uint8_t uid[12];tx15_usb_hw_uid(uid);
    unsigned nor_ok=jedec==0xc84018u && tx15_update_nor_init(&nor,pump,ticks,0,1000000u);
    struct tx15_update_flash_info observed;
    unsigned writable=nor_ok && tx15_update_nor_observe(&nor,&observed)
        && tx15_update_flash_writable(&observed);
    struct tx15_update_io io={&nor,tx15_update_nor_observe,tx15_update_nor_read,
        tx15_update_nor_erase4k,tx15_update_nor_program,pump};
    /* Initialization faults may expose diagnostics, never a writable HELLO. */
    tx15_update_runtime_init(&runtime,&io,(uint8_t*)0xd0100000u,128u+TX15_UPDATE_IMAGE_MAX,
        (uint8_t*)0xd0200000u,0x100000u,uid,0,!(writable&&display_ok));
    if(probe_report.error) {
        runtime.read_only=1;runtime.receiver.status.state=TX15_ERROR;
        runtime.receiver.status.error=TX15_IO_ERROR;
    }
    struct tx15_update_reply shown={UINT32_MAX,0,0,0,0,0};
    struct tx15_update_power power={0};
    if(tx15_usb_init()) {
        struct tx15_update_reply error={TX15_ERROR,TX15_IO_ERROR,0,0,0,0};
        if(display_ok)tx15_update_screen(&error,0,0);
        for(;;)__asm volatile("nop");
    }
    started=1;__asm volatile("cpsie i");
    uint32_t last_draw=0;unsigned last_connected=2;
    for(;;) {
        pump(0);
        if(runtime.committed && runtime.tx.active)(void)tx15_update_runtime_step(&runtime);
        struct tx15_update_reply status=runtime.committed?runtime.tx.status:runtime.receiver.status;
        uint32_t now=tx15_usb_ms();unsigned connected=(unsigned)tx15_usb_connected();
        if(display_ok && (last_connected!=connected || shown.state!=status.state
            || shown.error!=status.error || ((uint32_t)(now-last_draw)>=250 && memcmp(&shown,&status,sizeof(status))))) {
            tx15_update_screen(&status,connected,!runtime.read_only);
            shown=status;last_connected=connected;last_draw=now;
        }
        unsigned busy=runtime.committed && runtime.tx.active;
        if(tx15_update_power_poll(&power,now,!!(tx15_power_status()&TX15_BUTTON_PRESSED),busy)) {
            tx15_usb_stop();tx15_boot_qspi_stop();R(0x58020018u)=1u<<26; /* backlight off */
            R(0x58021c18u)=1u<<28; /* PH12 power hold low */
            for(;;)__asm volatile("nop");
        }
    }
}
