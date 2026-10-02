/* GPL-3.0-or-later */
#include "crsf_params.h"
#include <string.h>
int crsf_params_init(struct crsf_params *p,unsigned count)
{
    if (count>CRSF_PARAM_COUNT) return 0;
    memset(p,0,sizeof(*p));p->count=count;p->current=1;p->remaining=256;
    return 1;
}
int crsf_params_request(const struct crsf_params *p,uint8_t payload[4])
{
    if (!p->current || p->current>p->count) return 0;
    payload[0]=0xee;payload[1]=0xea;payload[2]=(uint8_t)p->current;payload[3]=(uint8_t)p->chunk;
    return 1;
}
void crsf_params_restart(struct crsf_params *p)
{
    if (p->current && p->current<=p->count) p->lengths[p->current-1]=0;
    p->chunk=0;p->remaining=256;
}
int crsf_params_accept(struct crsf_params *p,const struct crsf_message *m)
{
    if (!p->current || p->current>p->count || m->type!=0x2b) return 0;
    if (m->size<5 || m->size>CRSF_LINK_PAYLOAD_MAX) return -1;
    if (m->payload[0]!=0xea || m->payload[1]!=0xee || m->payload[2]!=p->current) return 0;
    unsigned remaining=m->payload[3],len=m->size-4,index=p->current-1;
    if ((p->chunk && remaining+1!=p->remaining) || p->lengths[index]+len>CRSF_PARAM_BYTES) return -1;
    memcpy(p->data[index]+p->lengths[index],m->payload+4,len);
    p->lengths[index]+=len;
    if (remaining) {p->remaining=remaining;p->chunk++;return 1;}
    p->current++;p->chunk=0;p->remaining=256;
    return p->current>p->count?3:2;
}
