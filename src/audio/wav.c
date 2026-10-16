#include "wav.h"
#include <string.h>
enum {RIFF,CHUNK,FMT,SKIP};
static uint16_t le16(const uint8_t *p) {return (uint16_t)(p[0]|((uint16_t)p[1]<<8));}
static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static void header(struct nd_wav *w,unsigned phase,unsigned need) {
    w->phase=phase;w->need=need;w->have=0;
}
static void skip(struct nd_wav *w,uint32_t count) {
    w->skip=count;
    if(count)w->phase=SKIP;else header(w,CHUNK,8);
}
void nd_wav_init(struct nd_wav *w,uint32_t bytes) {
    memset(w,0,sizeof(*w));w->file_bytes=w->end=bytes;
    header(w,RIFF,12);if(bytes<12)w->status=ND_WAV_TRUNCATED;
}
static int format(struct nd_wav *w) {
    const uint8_t *p=w->header;
    unsigned bits=le16(p+14),align=le16(p+12);uint32_t rate=le32(p+4);
    if(le16(p)!=1 || le16(p+2)!=1 || (bits!=8 && bits!=16)
       || (rate!=8000 && rate!=16000 && rate!=32000)
       || align!=bits/8 || le32(p+8)!=rate*align
       || (w->need==18 && le16(p+16)>w->chunk_bytes-18))return ND_WAV_FORMAT;
    w->format.rate=rate;w->format.bits=(uint16_t)bits;w->format.align=(uint16_t)align;
    w->fmt_seen=1;skip(w,w->chunk_bytes-w->need+(w->chunk_bytes&1));return ND_WAV_MORE;
}
static int complete_header(struct nd_wav *w) {
    const uint8_t *p=w->header;
    if(w->phase==RIFF) {
        uint32_t size=le32(p+4);
        if(memcmp(p,"RIFF",4) || memcmp(p+8,"WAVE",4))return ND_WAV_BAD_RIFF;
        if(size<4 || size>w->file_bytes-8)return ND_WAV_LENGTH;
        w->end=size+8;header(w,CHUNK,8);return ND_WAV_MORE;
    }
    if(w->phase==FMT)return format(w);
    uint32_t size=le32(p+4),remaining=w->end-w->pos;
    if(size>remaining || (size&1)>remaining-size)return ND_WAV_LENGTH;
    w->chunk_bytes=size;
    if(!memcmp(p,"fmt ",4)) {
        if(w->fmt_seen || size<16 || size==17)return ND_WAV_FORMAT;
        header(w,FMT,size==16?16:18);
    } else if(!memcmp(p,"data",4)) {
        if(!w->fmt_seen)return ND_WAV_FORMAT;
        if(!size || size%w->format.align)return ND_WAV_LENGTH;
        w->format.data_bytes=size;w->format.data_offset=w->pos;
        w->format.frames=size/w->format.align;return ND_WAV_DATA;
    } else skip(w,size+(size&1));
    return ND_WAV_MORE;
}
int nd_wav_feed(struct nd_wav *w,const uint8_t *data,size_t bytes,size_t *used) {
    if(!used)return w->status=ND_WAV_LENGTH;
    *used=0;
    if(w->status!=ND_WAV_MORE)return w->status;
    if(!data && bytes)return w->status=ND_WAV_LENGTH;
    if(bytes>ND_WAV_FEED_LIMIT)bytes=ND_WAV_FEED_LIMIT;
    while(*used<bytes && w->status==ND_WAV_MORE) {
        if(w->pos>=w->end) {w->status=ND_WAV_TRUNCATED;break;}
        size_t count=bytes-*used;
        if(count>w->end-w->pos)count=w->end-w->pos;
        if(w->phase==SKIP) {
            if(count>w->skip)count=w->skip;
            w->skip-=(uint32_t)count;
        } else {
            if(count>w->need-w->have)count=w->need-w->have;
            memcpy(w->header+w->have,data+*used,count);w->have+=(unsigned)count;
        }
        *used+=count;w->pos+=(uint32_t)count;
        if(w->phase==SKIP) {
            if(!w->skip)header(w,CHUNK,8);
        } else if(w->have==w->need)w->status=complete_header(w);
    }
    return w->status;
}
int nd_wav_finish(struct nd_wav *w) {
    if(w->status==ND_WAV_MORE)w->status=ND_WAV_TRUNCATED;
    return w->status;
}
