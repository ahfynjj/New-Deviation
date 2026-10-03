#include "crsf_tools.h"
#include <string.h>
#define SETTLE_MS 200u
#define TIMEOUT_MS 3000u
void crsf_tools_init(struct crsf_tools *p,int enable_writes)
{ memset(p,0,sizeof(*p));p->enabled=!!enable_writes; }
int crsf_tools_kind(const struct crsf_tools *p,uint8_t type,const uint8_t *data,unsigned n)
{
    if(!data)return 0;
    if(type==0x28 && n==2 && data[0]==0 && data[1]==0xea)return CRSF_TOOL_PING;
    if(n!=4 || data[0]!=0xee || data[1]!=0xea)return 0;
    if(type==0x2c && data[2]>=1 && data[2]<=64)return CRSF_TOOL_READ;
    if(type!=0x2d)return 0;
    if(data[2]==0 && data[3]==0)return CRSF_TOOL_STATS;
    if(!p->enabled || p->report.state==CRSF_WRITE_WAIT || !data[2] || data[2]>64)return 0;
    const struct crsf_tool_field *f=&p->fields[data[2]];
    unsigned v=data[3];
    return f->ready && f->min<f->max && v>=f->min && v<=f->max
        && (f->nonempty[v/8]&(1u<<(v%8)))?CRSF_TOOL_WRITE:0;
}
void crsf_tools_tick(struct crsf_tools *p,uint32_t now)
{
    if(p->report.state==CRSF_WRITE_WAIT && (uint32_t)(now-p->report.started)>TIMEOUT_MS) {
        p->report.state=CRSF_WRITE_TIMEOUT;p->report.failed++;
    }
}
int crsf_tools_defer(const struct crsf_tools *p,uint8_t type,const uint8_t *data,unsigned n,uint32_t now)
{
    return crsf_tools_kind(p,type,data,n)==CRSF_TOOL_READ && p->report.state==CRSF_WRITE_WAIT
        && data[2]==p->report.id && (uint32_t)(now-p->report.started)<SETTLE_MS;
}
void crsf_tools_cancel(struct crsf_tools *p)
{
    if(p->report.state==CRSF_WRITE_WAIT)p->report.state=CRSF_WRITE_CANCELLED;
    p->request_active=0;
}
void crsf_tools_sent(struct crsf_tools *p,uint8_t type,const uint8_t *data,unsigned n,uint32_t now)
{
    int kind=crsf_tools_kind(p,type,data,n);
    if(kind==CRSF_TOOL_STATS) {p->report.stats++;return;}
    if(kind==CRSF_TOOL_WRITE) {
        struct crsf_tool_field *f=&p->fields[data[2]];
        p->report.state=CRSF_WRITE_WAIT;p->report.writes++;p->report.id=data[2];
        p->report.previous=f->value;p->report.expected=data[3];p->report.actual=f->value;
        p->report.started=now;p->pending_schema=f->schema;
        p->verify_read=0;p->request_active=0;return;
    }
    if(kind!=CRSF_TOOL_READ)return;
    p->report.reads++;unsigned id=data[2],chunk=data[3];
    p->request_active=0;
    if(chunk==0) {
        p->used=0;p->assembly_id=id;p->next_chunk=0;p->fields[id].ready=0;
        p->verify_read=p->report.state==CRSF_WRITE_WAIT && p->report.id==id
            && (uint32_t)(now-p->report.started)>=SETTLE_MS;
    } else if(p->assembly_id!=id || p->next_chunk!=chunk) {
        p->fields[id].ready=0;return;
    }
    p->request_id=id;p->request_chunk=chunk;p->request_active=1;
}
static int parse(struct crsf_tools *p,struct crsf_tool_field *f)
{
    const uint8_t *b=p->bytes;unsigned n=p->used;
    if(n<4 || b[1]!=9)return 0; /* Hidden and non-selection fields are not writable. */
    unsigned at=2;while(at<n && b[at])at++;if(at==n)return 0;at++;
    unsigned index=0,length=0;
    for(;at<n && b[at];at++) {
        if(b[at]==';') {
            if(index>=256)return 0;
            if(length)f->nonempty[index/8]|=(uint8_t)(1u<<(index%8));
            index++;length=0;
        } else length++;
    }
    if(at==n || index>=256)return 0;
    if(length)f->nonempty[index/8]|=(uint8_t)(1u<<(index%8));
    unsigned value_at=++at;
    if(n-at<5)return 0;
    f->value=b[at];f->min=b[at+1];f->max=b[at+2];
    at+=4;while(at<n && b[at])at++;if(at==n)return 0;
    if(f->min>f->max || f->max>index || f->value<f->min || f->value>f->max)return 0;
    if(!(f->nonempty[f->value/8]&(1u<<(f->value%8))))return 0;
    uint32_t hash=2166136261u;
    for(unsigned i=0;i<n;i++)if(i!=value_at)hash=(hash^b[i])*16777619u;
    f->schema=hash;f->ready=1;return 1;
}
void crsf_tools_receive(struct crsf_tools *p,const struct crsf_message *m,uint32_t now)
{
    crsf_tools_tick(p,now);
    if(m->type!=0x2b || m->size<5 || m->size>60 || m->payload[0]!=0xea || m->payload[1]!=0xee)return;
    unsigned id=m->payload[2],remain=m->payload[3];
    if(!p->request_active || id!=p->request_id)return;
    p->request_active=0;
    if((p->request_chunk && (p->remaining==0 || remain!=p->remaining-1))
        || m->size-4>sizeof(p->bytes)-p->used) {
        p->fields[id].ready=0;p->assembly_id=0;return;
    }
    memcpy(p->bytes+p->used,m->payload+4,m->size-4);p->used+=m->size-4;
    p->remaining=remain;p->next_chunk=p->request_chunk+1;
    if(remain)return;
    struct crsf_tool_field field={0};
    if(!parse(p,&field)) {p->fields[id].ready=0;p->assembly_id=0;return;}
    p->fields[id]=field;p->assembly_id=0;
    if(p->verify_read && p->report.state==CRSF_WRITE_WAIT && p->report.id==id) {
        p->report.actual=field.value;
        if(field.value==p->report.expected && field.schema==p->pending_schema) {
            p->report.state=CRSF_WRITE_VERIFIED;p->report.verified++;
        } else {p->report.state=CRSF_WRITE_MISMATCH;p->report.failed++;}
    }
}
