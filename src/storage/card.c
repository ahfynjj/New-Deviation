#include "card.h"
#include <string.h>
enum {POWER,GO_IDLE,IFCOND,APP,OPCOND,CID,RCA,CSD,SELECT,STATE,BLOCK,READ0,READBOOT};
#define R1_ERRORS 0xfdffe008u
static void release(struct nd_card *c) {
    if(c->active) {c->ops->stop(c->ctx);c->active=0;}
}
static void fail(struct nd_card *c,unsigned error) {
    release(c);c->report.error=error;c->report.state=ND_CARD_ERROR;c->pending=0;
}
void nd_card_stop(struct nd_card *c) {release(c);c->report.state=ND_CARD_OFF;c->pending=0;}
int nd_card_capacity(const uint32_t csd[4],uint64_t *blocks) {
    unsigned version=csd[0]>>30;
    if(version==1) {
        uint32_t size=((csd[1]&63)<<16)|(csd[2]>>16);
        *blocks=((uint64_t)size+1)*1024;return 1;
    }
    if(version==0) {
        unsigned bits=(csd[1]>>16)&15,mult=(csd[2]>>15)&7;
        uint32_t size=((csd[1]&1023)<<2)|(csd[2]>>30);
        if(bits<9 || bits>11)return 0;
        *blocks=((uint64_t)size+1)<<(mult+2+bits-9);
        return *blocks && *blocks<=0x800000ull;
    }
    return 0;
}
int nd_card_begin(struct nd_card *c,const struct nd_sd_ops *ops,void *ctx,uint32_t now) {
    if(c->report.state==ND_CARD_BUSY)return 0;
    release(c);memset(c,0,sizeof(*c));c->ops=ops;c->ctx=ctx;
    if(!ops || !ops->init || !ops->stop || !ops->command || !ops->response || !ops->read_start || !ops->read_poll) {
        c->report.state=ND_CARD_ERROR;c->report.error=ND_CARD_HW;return 0;
    }
    c->active=1;
    if(ops->init(ctx)) {fail(c,ND_CARD_HW);return 0;}
    c->report.state=ND_CARD_BUSY;c->phase=POWER;c->next=now+10;c->total_deadline=now+2000;
    c->started=c->last_poll=now;return 1;
}
static void command(struct nd_card *c,unsigned cmd,uint32_t arg,unsigned response,uint32_t now) {
    c->report.last_command=cmd;c->report.steps++;
    if(c->ops->command(c->ctx,cmd,arg,response)) {fail(c,ND_CARD_HW);return;}
    c->deadline=now+100;c->pending=1;
}
static void decoded(struct nd_card *c) {
    int fs=nd_volume_decode(c->sector,c->lba,c->span,c->report.blocks,&c->report.volume);
    if(fs<0) {fail(c,ND_CARD_VOLUME);return;}
    release(c);c->report.state=ND_CARD_READY;
}
static void received(struct nd_card *c) {
    if(c->phase==READBOOT) {decoded(c);return;}
    int kind=nd_volume_partition(c->sector,c->report.blocks,&c->lba,&c->span);
    if(kind<0) {fail(c,ND_CARD_PARTITION);return;}
    c->report.partition_kind=(unsigned)kind;
    if(kind==ND_VOLUME_GPT) {release(c);c->report.state=ND_CARD_READY;return;}
    if(kind==ND_VOLUME_SUPER)decoded(c);else c->phase=READBOOT;
}
static void response(struct nd_card *c,uint32_t r[4],uint32_t now) {
    c->report.last_response=r[0];
    switch(c->phase) {
    case GO_IDLE:c->phase=IFCOND;c->next=now+2;break;
    case IFCOND:
        if(r[0]!=0x1aa) {fail(c,ND_CARD_PROTOCOL);return;}
        c->v2=1;c->phase=APP;break;
    case APP:
        if((r[0]&R1_ERRORS) || !(r[0]&32)) {fail(c,ND_CARD_PROTOCOL);return;}
        c->phase=OPCOND;break;
    case OPCOND:
        c->report.ocr=r[0];
        if(!(r[0]&0x00ff8000u)) {fail(c,ND_CARD_PROTOCOL);return;}
        if(!(r[0]&0x80000000u)) {c->phase=APP;c->next=now+10;break;}
        c->report.high_capacity=(r[0]>>30)&1;
        if(c->report.high_capacity && !c->v2) {fail(c,ND_CARD_PROTOCOL);return;}
        c->phase=CID;break;
    case CID:memcpy(c->report.cid,r,16);c->phase=RCA;break;
    case RCA:
        if((r[0]&0xe000) || !(r[0]>>16)) {fail(c,ND_CARD_PROTOCOL);return;}
        c->report.rca=r[0]>>16;c->phase=CSD;break;
    case CSD:
        memcpy(c->report.csd,r,16);
        if(!nd_card_capacity(r,&c->report.blocks) || ((r[0]>>30)==1)!=c->report.high_capacity) {fail(c,ND_CARD_CAPACITY);return;}
        c->phase=SELECT;break;
    case SELECT:case STATE:case BLOCK:
        if(r[0]&R1_ERRORS) {fail(c,ND_CARD_PROTOCOL);return;}
        if(c->phase==SELECT)c->phase=STATE;
        else if(c->phase==BLOCK)c->phase=READ0;
        else if((r[0]&0x1f00)==0x900)c->phase=c->report.high_capacity?READ0:BLOCK;
        else c->next=now+10;
        break;
    default:fail(c,ND_CARD_PROTOCOL);break;
    }
}
void nd_card_poll(struct nd_card *c,uint32_t now) {
    if(c->report.state!=ND_CARD_BUSY)return;
    c->report.elapsed=now-c->started;
    if(now-c->last_poll>c->report.max_gap)c->report.max_gap=now-c->last_poll;
    c->last_poll=now;
    if((int32_t)(now-c->total_deadline)>=0) {fail(c,ND_CARD_TIMEOUT);return;}
    if(c->pending) {
        uint32_t r[4]={0};
        int result=c->pending==1?c->ops->response(c->ctx,r):c->ops->read_poll(c->ctx,c->sector);
        if(!result && (int32_t)(now-c->deadline)<0)return;
        if(!result)result=ND_SD_TIMEOUT;
        unsigned pending=c->pending;c->pending=0;
        if(result<0) {
            if(pending==1 && c->phase==IFCOND && result==ND_SD_TIMEOUT) {c->v2=0;c->phase=APP;return;}
            fail(c,result==ND_SD_TIMEOUT?ND_CARD_TIMEOUT:pending==2?ND_CARD_IO:ND_CARD_PROTOCOL);return;
        }
        if(pending==1)response(c,r,now);else received(c);
        return;
    }
    if((int32_t)(now-c->next)<0)return;
    switch(c->phase) {
    case POWER:c->phase=GO_IDLE;command(c,0,0,ND_SD_NONE,now);break;
    case IFCOND:command(c,8,0x1aa,ND_SD_SHORT,now);break;
    case APP:command(c,55,0,ND_SD_SHORT,now);break;
    case OPCOND:command(c,41,0x00ff8000u|(c->v2?0x40000000u:0),ND_SD_OCR,now);break;
    case CID:command(c,2,0,ND_SD_LONG,now);break;
    case RCA:command(c,3,0,ND_SD_SHORT,now);break;
    case CSD:command(c,9,c->report.rca<<16,ND_SD_LONG,now);break;
    case SELECT:command(c,7,c->report.rca<<16,ND_SD_SHORT,now);break;
    case STATE:command(c,13,c->report.rca<<16,ND_SD_SHORT,now);break;
    case BLOCK:command(c,16,512,ND_SD_SHORT,now);break;
    case READ0:case READBOOT: {
        uint32_t lba=c->phase==READ0?0:c->lba;
        if((uint64_t)lba>=c->report.blocks || c->ops->read_start(c->ctx,lba,c->report.high_capacity)) {fail(c,ND_CARD_IO);return;}
        c->report.last_command=17;c->report.steps++;c->pending=2;c->deadline=now+250;break;
    }
    default:fail(c,ND_CARD_PROTOCOL);break;
    }
}
