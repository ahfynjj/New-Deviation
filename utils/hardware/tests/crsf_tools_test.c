#include "crsf_tools.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>
static struct crsf_tools policy;
static const uint8_t field[]={7,9,'M','a','x',' ','P','o','w','e','r',0,
    '1','0',';','2','5',';','5','0',0,1,0,2,0,'m','W',0};
static void request(unsigned id,unsigned chunk,uint32_t now)
{ uint8_t p[]={0xee,0xea,(uint8_t)id,(uint8_t)chunk};crsf_tools_sent(&policy,0x2c,p,4,now); }
static void response(unsigned id,unsigned remain,const uint8_t *data,unsigned size,uint32_t now)
{
    struct crsf_message m={.type=0x2b,.size=size+4,.payload={0xea,0xee,(uint8_t)id,(uint8_t)remain}};
    assert(size<=56);memcpy(m.payload+4,data,size);crsf_tools_receive(&policy,&m,now);
}
static void load(uint32_t now)
{ request(8,0,now);response(8,0,field,sizeof(field),now+1); }
int main(void)
{
    uint8_t stat[]={0xee,0xea,0,0},write[]={0xee,0xea,8,2};
    crsf_tools_init(&policy,0);load(10);
    assert(crsf_tools_kind(&policy,0x2d,stat,4)==CRSF_TOOL_STATS);
    assert(!crsf_tools_kind(&policy,0x2d,write,4));
    crsf_tools_init(&policy,1);
    response(8,0,field,sizeof(field),11);assert(!crsf_tools_kind(&policy,0x2d,write,4)); /* Unsolicited. */
    load(20);assert(crsf_tools_kind(&policy,0x2d,write,4)==CRSF_TOOL_WRITE);
    write[3]=3;assert(!crsf_tools_kind(&policy,0x2d,write,4));write[3]=2;
    write[0]=0xef;assert(!crsf_tools_kind(&policy,0x2d,write,4));write[0]=0xee;
    assert(!crsf_tools_kind(&policy,0x2d,write,3));
    crsf_tools_sent(&policy,0x2d,write,4,100);
    assert(policy.report.state==CRSF_WRITE_WAIT && policy.report.previous==1 && policy.report.writes==1);
    assert(!crsf_tools_kind(&policy,0x2d,write,4));
    request(8,0,120);response(8,0,field,sizeof(field),121);
    assert(policy.report.state==CRSF_WRITE_WAIT); /* A premature read is not confirmation. */
    uint8_t updated[sizeof(field)];memcpy(updated,field,sizeof(field));updated[sizeof(field)-7]=2;
    request(8,0,310);response(8,0,updated,sizeof(updated),311);
    assert(policy.report.state==CRSF_WRITE_VERIFIED && policy.report.actual==2 && policy.report.verified==1);
    write[3]=1;crsf_tools_sent(&policy,0x2d,write,4,400);
    request(8,0,610);response(8,0,field,12,611);
    /* Separate chunks retain metadata only after complete, ordered assembly. */
    assert(policy.report.state==CRSF_WRITE_WAIT);
    request(8,0,620);response(8,1,field,12,621);
    request(8,1,630);response(8,0,field+12,sizeof(field)-12,631);
    assert(policy.report.state==CRSF_WRITE_VERIFIED && policy.report.verified==2 && policy.report.actual==1);
    write[3]=2;crsf_tools_sent(&policy,0x2d,write,4,700);
    request(8,0,910);response(8,0,field,sizeof(field),911);
    assert(policy.report.state==CRSF_WRITE_MISMATCH && policy.report.failed==1);
    crsf_tools_sent(&policy,0x2d,write,4,1000);crsf_tools_tick(&policy,4001);
    assert(policy.report.state==CRSF_WRITE_TIMEOUT && policy.report.failed==2);
    crsf_tools_sent(&policy,0x2d,write,4,5000);crsf_tools_cancel(&policy);
    assert(policy.report.state==CRSF_WRITE_CANCELLED);
    crsf_tools_init(&policy,1);assert(!crsf_tools_kind(&policy,0x2d,write,4));
    uint8_t command[]={0,13,'B','i','n','d',0,0,10,0};
    request(8,0,10);response(8,0,command,sizeof(command),11);
    assert(!crsf_tools_kind(&policy,0x2d,write,4));
    uint8_t malformed[sizeof(field)];memcpy(malformed,field,sizeof(field));malformed[1]|=128;
    request(8,0,20);response(8,0,malformed,sizeof(malformed),21);
    assert(!crsf_tools_kind(&policy,0x2d,write,4));
    /* Wrong chunk countdown and truncated options cannot authorize writes. */
    request(8,0,30);response(8,2,field,12,31);request(8,1,32);response(8,0,field+12,sizeof(field)-12,33);
    assert(!crsf_tools_kind(&policy,0x2d,write,4));
    request(8,0,40);response(8,0,field,20,41);assert(!crsf_tools_kind(&policy,0x2d,write,4));
    stat[3]=1;assert(!crsf_tools_kind(&policy,0x2d,stat,4));
    crsf_tools_init(&policy,1);load(10);crsf_tools_sent(&policy,0x2d,write,4,100);
    memcpy(malformed,updated,sizeof(field));malformed[12]='2'; /* Same index, changed schema. */
    request(8,0,310);response(8,0,malformed,sizeof(malformed),311);
    assert(policy.report.state==CRSF_WRITE_MISMATCH && !policy.report.verified);
    crsf_tools_init(&policy,1);load(10);crsf_tools_sent(&policy,0x2d,write,4,UINT32_MAX-50);
    crsf_tools_tick(&policy,2949);assert(policy.report.state==CRSF_WRITE_WAIT);
    crsf_tools_tick(&policy,2950);assert(policy.report.state==CRSF_WRITE_TIMEOUT);
    request(8,0,3000);response(8,0,updated,sizeof(updated),3001);
    assert(!policy.report.verified); /* Late read cannot turn a timeout into success. */
    const uint8_t blank[]={0,9,'S',0,'a',';',';','b',0,0,0,2,0,0};
    request(8,0,3100);response(8,0,blank,sizeof(blank),3101);
    write[3]=1;assert(!crsf_tools_kind(&policy,0x2d,write,4));
    uint8_t big[56];memset(big,'X',sizeof(big));
    for(unsigned i=0;i<10;i++) {request(8,i,4000+i*2);response(8,10-i,big,sizeof(big),4001+i*2);}
    assert(!crsf_tools_kind(&policy,0x2d,write,4)); /* >512 bytes discarded. */
    puts("CRSF statistics, typed selections, ordered chunks, write/readback/mismatch/timeout/cancel PASS");
}
