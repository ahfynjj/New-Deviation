/* Native update dispatcher; GPL-3.0-or-later. */
#include "runtime.h"
#include <string.h>
void tx15_update_runtime_init(struct tx15_update_runtime *r,const struct tx15_update_io *io,
                              uint8_t *ram,size_t cap,uint8_t *shadow,size_t shadow_cap,
                              const uint8_t uid[12],uint64_t session,unsigned read_only)
{
    memset(r,0,sizeof(*r));r->io=*io;r->shadow=shadow;r->shadow_capacity=shadow_cap;
    memcpy(r->uid,uid,12);r->read_only=!!read_only;
    tx15_update_receiver_init(&r->receiver,ram,cap,session,1,1);
}
void tx15_update_runtime_session(struct tx15_update_runtime *r,uint64_t session)
{
    if (r->committed) r->receiver.session=session;
    else {
        uint8_t *p=r->receiver.staging;size_t n=r->receiver.capacity;
        tx15_update_receiver_init(&r->receiver,p,n,session,1,1);
    }
}
void tx15_update_runtime_request(struct tx15_update_runtime *r,const struct tx15_frame *f,struct tx15_frame *out)
{
    memset(out,0,sizeof(*out));out->kind=f->kind|0x80;out->sequence=f->sequence;
    out->offset=f->offset;out->session=r->receiver.session;out->bytes=24;
    struct tx15_update_reply status=r->committed?r->tx.status:r->receiver.status;
    if (f->kind==TX15_HELLO && !f->session && !f->bytes) {
        struct tx15_update_flash_info info={0};
        /* During a busy NOR command never issue a nested observation. */
        unsigned observed=!r->committed && r->io.observe(r->io.ctx,&info);
        unsigned writable=observed && tx15_update_flash_writable(&info) && !r->read_only && r->synchronized;
        out->bytes=48;memcpy(out->payload,r->uid,12);
        const uint32_t fields[]={1,1,TX15_UPDATE_IMAGE_MAX,writable?2u:1u,
                                info.jedec,info.capacity,info.page_bytes,info.erase_bytes};
        for (unsigned i=0;i<8;i++) tx15_update_put_word(out->payload+12+i*4,fields[i]);
        out->payload[44]=info.sr1;out->payload[45]=info.sr2;out->payload[46]=info.sr3;
        out->payload[47]=info.sfdp_valid;return;
    }
    if (!r->receiver.session || f->session!=r->receiver.session) status.error=TX15_BAD_SESSION;
    else if (r->committed) {
        if (f->kind!=TX15_STATUS || f->bytes) status.error=TX15_BAD_STATE;
    } else if (f->kind==TX15_READ_SETTINGS) {
        uint32_t n=f->bytes==4?tx15_update_word(f->payload):0;
        if (!n || n>1024 || f->offset>=65536 || n>65536-f->offset) status.error=TX15_BAD_OFFSET;
        else if (!r->io.read(r->io.ctx,0xf0000+f->offset,out->payload,n)) status.error=TX15_IO_ERROR;
        else {out->bytes=n;return;}
    } else if (f->kind==TX15_COMMIT) {
        if (r->read_only) status.error=TX15_READ_ONLY;
        else if (!r->synchronized) status.error=TX15_BAD_STATE;
        else if (f->bytes!=20 || memcmp(f->payload,r->uid,12)) status.error=TX15_BAD_IDENTITY;
        else if (!tx15_update_receiver_request(&r->receiver,f,&status)) { /* typed error already set */ }
        else {
            /* Freeze all dispatcher mutation before preparation calls USB
             * service. Duplicate COMMIT, DATA and ABORT cannot reenter. */
            r->committed=1;r->tx.status=status;r->tx.status.state=TX15_VALIDATING;
            if (!tx15_update_tx_prepare(&r->tx,&r->io,&r->receiver.package,r->shadow,r->shadow_capacity)) {
                r->tx.status.state=TX15_ERROR;r->tx.status.error=TX15_IO_ERROR;
            }
            status=r->tx.status;
        }
    } else tx15_update_receiver_request(&r->receiver,f,&status);
    const uint32_t fields[]={status.state,status.error,status.received,status.total,status.image_crc,status.verification_flags};
    for (unsigned i=0;i<6;i++) tx15_update_put_word(out->payload+i*4,fields[i]);
    out->session=r->receiver.session;
}
int tx15_update_runtime_step(struct tx15_update_runtime *r)
{ return r->committed?tx15_update_tx_step(&r->tx):0; }
