/* GPL-3.0-or-later */
#include "crsf_stream.h"
#include <string.h>
static int sync_byte(uint8_t b) {return b==0xea || b==0xc8 || b==0 || b==0xee;}
static void drop(struct crsf_stream *s) {
    if (s->size) {s->size--;memmove(s->bytes,s->bytes+1,s->size);}
}
int crsf_stream_feed(struct crsf_stream *s,uint8_t byte,uint32_t ms,struct crsf_frame *frame)
{
    if ((uint32_t)(ms-s->last_ms)>10 || s->size>=64) s->size=0;
    s->last_ms=ms;
    s->bytes[s->size++]=byte;
    while (s->size) {
        if (!sync_byte(s->bytes[0])) {drop(s);continue;}
        if (s->size<2) break;
        unsigned len=s->bytes[1];
        if (len<2 || len>62) {drop(s);continue;}
        if (s->size<len+2) break;
        frame->size=len+2;memcpy(frame->bytes,s->bytes,frame->size);
        if (crsf_frame_valid(frame)) {
            s->size-=frame->size;
            memmove(s->bytes,s->bytes+frame->size,s->size);
            return 1;
        }
        drop(s);
    }
    return 0;
}
static uint32_t be32(const uint8_t *p) {
    return (uint32_t)p[0]<<24 | (uint32_t)p[1]<<16 | (uint32_t)p[2]<<8 | p[3];
}
int crsf_device_info(const struct crsf_frame *f,struct crsf_device *d)
{
    if (!d || !crsf_frame_valid(f) || f->bytes[2]!=0x29 || f->size<20
        || f->bytes[3]!=0xea || f->bytes[4]!=0xee) return 0;
    unsigned end=5;
    while (end<f->size-1 && f->bytes[end]) end++;
    /* NUL, serial, hardware, software, field count, parameter version, CRC */
    if (end+16>f->size) return 0;
    unsigned count=end-5;
    if (count>=sizeof(d->name)) count=sizeof(d->name)-1;
    memcpy(d->name,f->bytes+5,count);d->name[count]=0;
    d->serial=be32(f->bytes+end+1);d->hardware=be32(f->bytes+end+5);
    d->software=be32(f->bytes+end+9);d->fields=f->bytes[end+13];
    return 1;
}
