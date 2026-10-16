#include "pcm.h"
#include <string.h>
int nd_pcm_init(struct nd_pcm *c,const struct nd_wav_format *f) {
    memset(c,0,sizeof(*c));
    if(!f || (f->rate!=8000 && f->rate!=16000 && f->rate!=32000)
       || (f->bits!=8 && f->bits!=16) || f->align!=f->bits/8 || !f->frames
       || f->data_bytes%f->align || f->data_bytes/f->align!=f->frames)
        return c->status=ND_PCM_FORMAT;
    c->bits=f->bits;c->ratio=32000/f->rate;c->frames=f->frames;return ND_PCM_MORE;
}
static int sample(struct nd_pcm *c,const uint8_t *data,size_t bytes,size_t *used,int32_t *out) {
    if(c->read==c->frames)return 0;
    if(c->bits==8) {
        if(*used==bytes)return 0;
        *out=((int32_t)data[(*used)++]-128)*256;
    } else {
        if(!c->have_low) {
            if(*used==bytes)return 0;
            c->low=data[(*used)++];c->have_low=1;
        }
        if(*used==bytes)return 0;
        int32_t value=(int32_t)c->low|((int32_t)data[(*used)++]<<8);
        *out=value>=32768?value-65536:value;c->have_low=0;
    }
    c->read++;return 1;
}
int nd_pcm_process(struct nd_pcm *c,const uint8_t *data,size_t bytes,size_t *used,
                   int16_t *out,size_t capacity,size_t *written) {
    if(!used || !written)return c->status=ND_PCM_FORMAT;
    *used=*written=0;
    if(c->status!=ND_PCM_MORE)return c->status;
    if((!data && bytes) || (!out && capacity))return c->status=ND_PCM_FORMAT;
    if(bytes>ND_PCM_INPUT_LIMIT)bytes=ND_PCM_INPUT_LIMIT;
    if(capacity>ND_PCM_OUTPUT_LIMIT)capacity=ND_PCM_OUTPUT_LIMIT;
    while(*written<capacity) {
        if(!c->have_previous) {
            if(!sample(c,data,bytes,used,&c->previous))break;
            c->have_previous=1;
        }
        if(!c->have_pair) {
            if(c->read==c->frames)c->next=c->previous;
            else if(!sample(c,data,bytes,used,&c->next))break;
            c->have_pair=1;
        }
        int32_t value=c->previous+(c->next-c->previous)*(int32_t)c->phase/(int32_t)c->ratio;
        out[(*written)++]=(int16_t)value;
        if(++c->phase==c->ratio) {
            if(++c->emitted==c->frames) {c->status=ND_PCM_DONE;break;}
            c->previous=c->next;c->have_pair=0;c->phase=0;
        }
    }
    return c->status;
}
int nd_pcm_finish(struct nd_pcm *c) {
    if(c->status==ND_PCM_MORE && (c->read<c->frames || c->have_low))c->status=ND_PCM_TRUNCATED;
    return c->status;
}
