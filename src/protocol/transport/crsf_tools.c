#include "crsf_tools.h"
#include <string.h>
#define SETTLE_MS 200u
#define TIMEOUT_MS 3000u
#define COMMAND_LIMIT_MS 300000u
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
    if(!p->enabled || !data[2] || data[2]>64)return 0;
    unsigned v=data[3];
    if(p->command_active) {
        if(data[2]!=p->report.id || p->cancel_sent)return 0;
        return v==5 || v==6 || (v==4 && p->report.actual==3)?CRSF_TOOL_COMMAND:0;
    }
    if(p->report.state==CRSF_WRITE_WAIT)return 0;
    const struct crsf_tool_field *f=&p->fields[data[2]];
    if(f->ready && f->type==13)return f->value==0 && v==1?CRSF_TOOL_COMMAND:0;
    return f->ready && f->min<f->max && v>=f->min && v<=f->max
        && (f->nonempty[v/8]&(1u<<(v%8)))?CRSF_TOOL_WRITE:0;
}
void crsf_tools_tick(struct crsf_tools *p,uint32_t now)
{
    if(p->command_active) {
        /* Confirmation waits for a human; queries cannot keep a silent
         * module alive. A session also has an absolute five-minute bound. */
        if((uint32_t)(now-p->report.started)<=COMMAND_LIMIT_MS
            && ((!p->cancel_sent && p->report.actual==3) || (uint32_t)(now-p->command_feedback)<=TIMEOUT_MS))return;
        p->fields[p->report.id].ready=0;p->command_active=p->command_reply=0;
        p->request_active=0;p->report.state=CRSF_WRITE_TIMEOUT;p->report.failed++;return;
    }
    if(p->report.state==CRSF_WRITE_WAIT && (uint32_t)(now-p->report.started)>TIMEOUT_MS) {
        p->report.state=CRSF_WRITE_TIMEOUT;p->report.failed++;
    }
}
const char *crsf_tools_error(const struct crsf_tools *p)
{
    if(!p->report.command)return NULL;
    if(p->report.state==CRSF_WRITE_TIMEOUT)return "ELRS command timeout; module action is unconfirmed";
    if(p->report.state==CRSF_WRITE_MISMATCH)return "ELRS command reply changed; module action is unconfirmed";
    return NULL;
}
int crsf_tools_defer(const struct crsf_tools *p,uint8_t type,const uint8_t *data,unsigned n,uint32_t now)
{
    int kind=crsf_tools_kind(p,type,data,n);
    /* Drain a popup's complete reply before any next control action. Otherwise
     * a queued CONFIRM/POLL can interleave a new first chunk with Lua's tail. */
    if(kind==CRSF_TOOL_COMMAND && p->assembly_id==p->report.id && p->remaining)return 1;
    return kind==CRSF_TOOL_READ && !p->report.command && p->report.state==CRSF_WRITE_WAIT
        && data[2]==p->report.id && (uint32_t)(now-p->report.started)<SETTLE_MS;
}
int crsf_tools_command_chunk(const struct crsf_tools *p,uint8_t payload[4])
{
    if(!p->command_active || p->request_active || p->assembly_id!=p->report.id
        || !p->remaining || !p->next_chunk)return 0;
    payload[0]=0xee;payload[1]=0xea;payload[2]=(uint8_t)p->report.id;payload[3]=(uint8_t)p->next_chunk;
    return 1;
}
void crsf_tools_cancel(struct crsf_tools *p)
{
    if(p->report.state==CRSF_WRITE_WAIT)p->report.state=CRSF_WRITE_CANCELLED;
    p->command_active=p->command_reply=p->request_active=0;
}
void crsf_tools_sent(struct crsf_tools *p,uint8_t type,const uint8_t *data,unsigned n,uint32_t now)
{
    int kind=crsf_tools_kind(p,type,data,n);
    if(kind==CRSF_TOOL_STATS) {p->report.stats++;return;}
    if(kind==CRSF_TOOL_COMMAND) {
        unsigned id=data[2],v=data[3];
        if(v==1) {
            p->report.command=1;p->report.commands++;p->report.id=id;
            p->report.started=now;p->report.previous=p->fields[id].value;
            p->pending_schema=p->fields[id].schema;p->cancel_sent=0;
            p->command_active=1;
        } else if(v==4)p->report.confirmed++;
        else if(v==6)p->report.polled++;
        else {p->report.cancelled++;p->cancel_sent=1;}
        if(v!=6) {p->report.actual=v;p->command_feedback=now;}
        p->report.expected=v;p->report.state=CRSF_WRITE_WAIT;
        p->command_reply=1;p->request_active=p->verify_read=0;return;
    }
    if(kind==CRSF_TOOL_WRITE) {
        struct crsf_tool_field *f=&p->fields[data[2]];
        p->report.command=0;p->report.state=CRSF_WRITE_WAIT;p->report.writes++;p->report.id=data[2];
        p->report.previous=f->value;p->report.expected=data[3];p->report.actual=f->value;
        p->report.started=now;p->pending_schema=f->schema;
        p->verify_read=0;p->request_active=0;return;
    }
    if(kind!=CRSF_TOOL_READ)return;
    p->report.reads++;unsigned id=data[2],chunk=data[3];
    p->request_active=0;
    if(chunk==0) {
        p->used=0;p->assembly_id=id;p->next_chunk=0;p->fields[id].ready=0;
        p->verify_read=!p->report.command && p->report.state==CRSF_WRITE_WAIT && p->report.id==id
            && (uint32_t)(now-p->report.started)>=SETTLE_MS;
    } else if(p->assembly_id!=id || p->next_chunk!=chunk) {
        p->fields[id].ready=0;return;
    }
    p->request_id=id;p->request_chunk=chunk;p->request_active=1;
}
static int parse(struct crsf_tools *p,struct crsf_tool_field *f)
{
    const uint8_t *b=p->bytes;unsigned n=p->used;
    if(n<4 || (b[1]!=9 && b[1]!=13))return 0; /* Hidden/unsupported fields stay blocked. */
    unsigned at=2;while(at<n && b[at])at++;if(at==n)return 0;at++;
    f->type=b[1];
    if(f->type==13) {
        if(n-at<3 || (b[at]!=0 && b[at]!=2 && b[at]!=3))return 0;
        f->value=b[at];unsigned info=at+2;
        while(info<n && b[info])info++;
        if(info!=n-1)return 0;
        /* Status, polling interval and progress text change during execution.
         * Bind authorization to the static parent/type/name identity. */
        uint32_t hash=2166136261u;
        for(unsigned i=0;i<at;i++)hash=(hash^b[i])*16777619u;
        f->schema=hash;f->ready=1;return 1;
    }
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
    if(!p->request_active || id!=p->request_id) {
        /* Commands answer writes directly with a field definition. Permit
         * one first chunk only after an accepted command on this session. */
        if(!p->command_active || !p->command_reply || id!=p->report.id)return;
        p->command_reply=0;p->used=0;p->assembly_id=id;p->request_chunk=0;p->verify_read=0;
    }
    p->request_active=0;
    if((p->request_chunk && (p->remaining==0 || remain!=p->remaining-1))
        || m->size-4>sizeof(p->bytes)-p->used) {
        p->fields[id].ready=0;p->assembly_id=0;return;
    }
    memcpy(p->bytes+p->used,m->payload+4,m->size-4);p->used+=m->size-4;
    p->remaining=remain;p->next_chunk=p->request_chunk+1;
    if(remain)return;
    struct crsf_tool_field field={0};
    int valid=parse(p,&field);
    if(p->command_active && p->report.id==id) {
        p->command_reply=0;
        if(!valid || field.type!=13 || field.schema!=p->pending_schema) {
            p->fields[id].ready=0;p->assembly_id=0;p->command_active=0;
            p->report.state=CRSF_WRITE_MISMATCH;p->report.failed++;return;
        }
        p->command_feedback=now;p->report.actual=field.value;
        if(field.value==0) {
            p->command_active=0;
            p->report.state=p->cancel_sent?CRSF_WRITE_CANCELLED:CRSF_COMMAND_COMPLETE;
            if(!p->cancel_sent)p->report.completed++;
        }
    }
    if(!valid) {p->fields[id].ready=0;p->assembly_id=0;return;}
    p->fields[id]=field;p->assembly_id=0;
    if(p->verify_read && p->report.state==CRSF_WRITE_WAIT && p->report.id==id) {
        p->report.actual=field.value;
        if(field.value==p->report.expected && field.schema==p->pending_schema) {
            p->report.state=CRSF_WRITE_VERIFIED;p->report.verified++;
        } else {p->report.state=CRSF_WRITE_MISMATCH;p->report.failed++;}
    }
}
