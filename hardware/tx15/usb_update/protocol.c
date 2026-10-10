/* New Deviation native USB update framing; GPL-3.0-or-later. */
#include "protocol.h"
#include <string.h>
uint32_t tx15_update_word(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
void tx15_update_put_word(uint8_t *p,uint32_t v)
{ for (unsigned i=0;i<4;i++) p[i]=(uint8_t)(v>>(i*8)); }
void tx15_update_frame_init(struct tx15_frame_parser *p) { if (p) p->used=0; }
static void discard(struct tx15_frame_parser *p,size_t n)
{ p->used-=n; memmove(p->buffer,p->buffer+n,p->used); }
int tx15_update_frame_feed(struct tx15_frame_parser *p,const uint8_t *data,size_t n,
                           tx15_frame_callback cb,void *ctx)
{
    if (!p || (!data && n) || !cb) return -1;
    int accepted=0;
    while (n--) {
        if (p->used>=sizeof(p->buffer)) discard(p,1);
        p->buffer[p->used++]=*data++;
        while (p->used>=4) {
            const uint8_t *b=p->buffer;
            if (memcmp(b,"NDU1",4)) { discard(p,1); continue; }
            if (p->used<32) break;
            uint32_t bytes=tx15_update_word(b+24);
            if (b[4]!=1 || b[6] || b[7] || bytes>TX15_FRAME_PAYLOAD_MAX) { discard(p,1); continue; }
            if (p->used<32u+bytes) break;
            uint32_t crc=tx15_update_crc(tx15_update_crc(0,b,28),b+32,bytes);
            if (crc!=tx15_update_word(b+28)) { discard(p,1); continue; }
            struct tx15_frame f;
            f.kind=b[5]; f.session=(uint64_t)tx15_update_word(b+8)|((uint64_t)tx15_update_word(b+12)<<32);
            f.sequence=tx15_update_word(b+16); f.offset=tx15_update_word(b+20); f.bytes=bytes;
            memcpy(f.payload,b+32,bytes);
            /* Consume before callback: callback may reset the parser on reconnect. */
            discard(p,32u+bytes); cb(ctx,&f); accepted++;
        }
    }
    return accepted;
}
size_t tx15_update_frame_encode(const struct tx15_frame *f,uint8_t *out,size_t capacity)
{
    if (!f || !out || f->bytes>TX15_FRAME_PAYLOAD_MAX || capacity<32u+f->bytes) return 0;
    memcpy(out,"NDU1",4); out[4]=1;out[5]=f->kind;out[6]=out[7]=0;
    tx15_update_put_word(out+8,(uint32_t)f->session);
    tx15_update_put_word(out+12,(uint32_t)(f->session>>32));
    tx15_update_put_word(out+16,f->sequence);tx15_update_put_word(out+20,f->offset);
    tx15_update_put_word(out+24,f->bytes);memcpy(out+32,f->payload,f->bytes);
    tx15_update_put_word(out+28,tx15_update_crc(tx15_update_crc(0,out,28),out+32,f->bytes));
    return 32u+f->bytes;
}
