/* Temporary USB probe: no NOR mutation code is linked. GPL-3.0-or-later. */
#include "usb_board.h"
#include "usb_hw.h"
#include "receiver.h"
#include "../board/power.h"
#define REG(a) (*(volatile uint32_t *)(uintptr_t)(a))
volatile uint32_t usb_probe_report[32] __attribute__((section(".mailbox"),aligned(8)));
static struct tx15_frame_parser parser;
static struct tx15_update_receiver receiver;
static uint8_t tx[TX15_FRAME_BYTES_MAX];static size_t tx_bytes,tx_sent;
void Boot_Fault(void)
{
    usb_probe_report[2]=8;usb_probe_report[3]=REG(0xe000ed28u);
    __asm volatile("cpsid i");for (;;) __asm volatile("nop");
}
static void request(void *ctx,const struct tx15_frame *f)
{
    (void)ctx;struct tx15_frame out={0};struct tx15_update_reply status;
    int ok=tx15_update_receiver_request(&receiver,f,&status);
    out.kind=f->kind|0x80;out.sequence=f->sequence;out.offset=f->offset;out.session=receiver.session;
    if (ok && f->kind==TX15_HELLO) {
        out.bytes=48;tx15_usb_hw_uid(out.payload);
        const uint32_t info[8]={1,1,TX15_UPDATE_IMAGE_MAX,1,0xc84018,0x1000000,256,4096};
        for (unsigned i=0;i<8;i++) tx15_update_put_word(out.payload+12+i*4,info[i]);
        /* Probe reports geometry as reference-only, sfdp_valid=0, read_only=1. */
    } else {
        if (f->kind==TX15_COMMIT) status.error=TX15_READ_ONLY;
        out.bytes=24;
        const uint32_t fields[]={status.state,status.error,status.received,status.total,status.image_crc,0};
        for (unsigned i=0;i<6;i++) tx15_update_put_word(out.payload+i*4,fields[i]);
    }
    tx_bytes=tx15_update_frame_encode(&out,tx,sizeof(tx));tx_sent=0;
    usb_probe_report[7]++;usb_probe_report[8]=status.state;
    usb_probe_report[9]=status.received;
}
void Boot_Main(void)
{
    /* Host launches only after the frozen RAM initializer proved PLL128,
     * SDRAM, PH12 and thread-mode halt. Never inherit the application PC. */
    usb_probe_report[0]=0x55534231u;usb_probe_report[1]=1;usb_probe_report[2]=1;
    if ((REG(0x58024410u)&0x3fu)!=0x1bu || (REG(0x58024418u)&0xf7fu)!=0x48u
        || (REG(0xe000ed14u)&0x30000u) || (REG(0xe000ed94u)&1u)) { usb_probe_report[3]=1;Boot_Fault(); }
    tx15_power_init();
    if ((tx15_power_status()&15u)!=15u || tx15_usb_init()) { usb_probe_report[3]=2;Boot_Fault(); }
    tx15_update_frame_init(&parser);uint32_t epoch=UINT32_MAX;
    usb_probe_report[2]=3;__asm volatile("cpsie i");
    for (;;) {
        tx15_usb_poll();
        if (epoch!=tx15_usb_epoch()) {
            epoch=tx15_usb_epoch();uint64_t session=0;
            (void)tx15_usb_new_session(&session);
            tx15_update_receiver_init(&receiver,(uint8_t *)0xd0100000u,128u+TX15_UPDATE_IMAGE_MAX,session,1,1);
            tx15_update_frame_init(&parser);tx_bytes=tx_sent=0;
            usb_probe_report[5]=(uint32_t)session;usb_probe_report[6]=(uint32_t)(session>>32);
        }
        tx15_update_receiver_tick(&receiver,tx15_usb_ms());
        if (tx_sent<tx_bytes) tx_sent+=tx15_usb_write(tx+tx_sent,tx_bytes-tx_sent);
        else {
            uint8_t byte;
            /* Stop after each reply to avoid overwriting a queued response. */
            for (unsigned i=0;i<2048 && tx_sent>=tx_bytes && tx15_usb_read(&byte,1);i++)
                tx15_update_frame_feed(&parser,&byte,1,request,NULL);
        }
        if (!receiver.session && tx15_usb_connected()) epoch=UINT32_MAX;
        usb_probe_report[4]=tx15_usb_ms();usb_probe_report[10]=tx15_usb_connected();
        usb_probe_report[11]=tx15_usb_synchronized();
    }
}
