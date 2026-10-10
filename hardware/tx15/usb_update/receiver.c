/* New Deviation RAM-only update receiver; GPL-3.0-or-later. */
#include "receiver.h"
#include <string.h>
void tx15_update_receiver_init(struct tx15_update_receiver *r,uint8_t *p,size_t n,
                               uint64_t session,uint32_t api,uint32_t abi)
{
    memset(r,0,sizeof(*r));r->staging=p;r->capacity=n;r->session=session;
    r->boot_api=api;r->settings_abi=abi;
}
static void invalidate(struct tx15_update_receiver *r,uint32_t state,uint32_t error)
{
    if (r->staging && r->capacity>=128) memset(r->staging,0,128);
    memset(&r->package,0,sizeof(r->package));memset(&r->status,0,sizeof(r->status));
    r->status.state=state;r->status.error=error;r->session=0;
}
void tx15_update_receiver_tick(struct tx15_update_receiver *r,uint32_t now)
{
    r->now=now;
    if (r->status.state==TX15_RECEIVING &&
        ((uint32_t)(now-r->last_activity)>=30000u || (uint32_t)(now-r->start)>=300000u))
        invalidate(r,TX15_ERROR,TX15_TIMEOUT);
}
int tx15_update_receiver_request(struct tx15_update_receiver *r,const struct tx15_frame *f,
                                 struct tx15_update_reply *reply)
{
    if (!r || !f || !reply) return 0;
    uint32_t error=TX15_OK;
    if (f->bytes>1024) error=TX15_BAD_REQUEST;
    else if (f->kind==TX15_HELLO && !f->session && !f->bytes) { /* No mutation. */ }
    else if (!r->session || f->session!=r->session) error=TX15_BAD_SESSION;
    else if (f->kind==TX15_STATUS && !f->bytes) { /* No mutation. */ }
    else if (f->kind==TX15_ABORT) {
        if (f->bytes || r->status.state>=TX15_ERASING) error=TX15_BAD_STATE;
        else invalidate(r,TX15_IDLE,TX15_OK); /* Runtime issues a fresh RNG session. */
    } else if (f->kind==TX15_BEGIN) {
        if (r->status.state!=TX15_IDLE || f->bytes!=128 || f->offset) error=TX15_BAD_STATE;
        else if (f->sequence!=1) error=TX15_BAD_SEQUENCE;
        else {
            uint32_t n=tx15_update_header_validate(f->payload,r->boot_api,r->settings_abi);
            if (!n || !r->staging || r->capacity<128u+n) error=TX15_BAD_PACKAGE;
            else {
                memcpy(r->staging,f->payload,128); r->status.state=TX15_RECEIVING;
                r->status.total=n; r->status.image_crc=tx15_update_word(f->payload+20);
                r->start=r->last_activity=r->now;r->next_sequence=2;
            }
        }
    } else if (f->kind==TX15_DATA) {
        if (r->status.state!=TX15_RECEIVING || !f->bytes) error=TX15_BAD_STATE;
        else if (f->sequence==r->last_sequence && f->offset==r->last_offset
                 && f->bytes==r->last_bytes && r->last_bytes
                 && !memcmp(r->staging+128+r->last_offset,f->payload,f->bytes)) r->last_activity=r->now;
        else if (f->sequence!=r->next_sequence || f->sequence==UINT32_MAX) error=TX15_BAD_SEQUENCE;
        else if (f->offset!=r->status.received || f->bytes>r->status.total-r->status.received) error=TX15_BAD_OFFSET;
        else {
            memcpy(r->staging+128+f->offset,f->payload,f->bytes);
            r->last_sequence=f->sequence;r->last_offset=f->offset;r->last_bytes=f->bytes;
            r->next_sequence++;r->status.received+=f->bytes;r->last_activity=r->now;
        }
    } else if (f->kind==TX15_FINALIZE) {
        if (f->bytes || f->offset) error=TX15_BAD_REQUEST;
        else if (r->status.state==TX15_READY && f->sequence==r->final_sequence) { /* Retry. */ }
        else if (r->status.state!=TX15_RECEIVING || r->status.received!=r->status.total) error=TX15_BAD_STATE;
        else if (f->sequence!=r->next_sequence || f->sequence==UINT32_MAX) error=TX15_BAD_SEQUENCE;
        else {
            r->status.state=TX15_VALIDATING;
            if (!tx15_update_package_validate(r->staging,128u+r->status.total,
                        r->boot_api,r->settings_abi,&r->package)) invalidate(r,TX15_ERROR,TX15_BAD_PACKAGE);
            else { r->status.state=TX15_READY;r->final_sequence=f->sequence; }
            error=r->status.error;
        }
    } else if (f->kind==TX15_COMMIT) {
        /* Only exposes READY to runtime, which must check UID/length/CRC and
         * independently revalidate NOR before performing any Flash operation. */
        if (r->status.state!=TX15_READY || f->bytes!=20) error=TX15_BAD_STATE;
        else if (tx15_update_word(f->payload+12)!=r->package.image_bytes
                 || tx15_update_word(f->payload+16)!=r->package.image_crc) error=TX15_BAD_PACKAGE;
    } else error=TX15_BAD_REQUEST;
    *reply=r->status;
    if (error) reply->error=error;
    return !error;
}
