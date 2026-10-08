#include "crsf_tools.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct crsf_tools p;
static const uint8_t field[]={0,13,'W','i','F','i',0,0,10,0};
static void read_field(unsigned chunk,uint32_t now)
{ uint8_t d[]={0xee,0xea,8,(uint8_t)chunk};crsf_tools_sent(&p,0x2c,d,4,now); }
static void reply(const uint8_t *b,unsigned n,unsigned remain,uint32_t now)
{
    struct crsf_message m={.type=0x2b,.size=n+4,.payload={0xea,0xee,8,(uint8_t)remain}};
    assert(n<=56);memcpy(m.payload+4,b,n);crsf_tools_receive(&p,&m,now);
}
static int allowed(unsigned v)
{ uint8_t d[]={0xee,0xea,8,(uint8_t)v};return crsf_tools_kind(&p,0x2d,d,4)!=0; }
static void send_command(unsigned v,uint32_t now)
{ uint8_t d[]={0xee,0xea,8,(uint8_t)v};assert(allowed(v));crsf_tools_sent(&p,0x2d,d,4,now); }
static void load(uint32_t now)
{ read_field(0,now);reply(field,sizeof(field),0,now+1); }
int main(void)
{
    crsf_tools_init(&p,1);
    reply(field,sizeof(field),0,0);assert(!allowed(1)); /* No unsolicited authorization. */
    load(10);assert(allowed(1)); /* Visible, complete command metadata. */
    assert(!allowed(0) && !allowed(2) && !allowed(3) && !allowed(4) && !allowed(5) && !allowed(6));
    assert(p.report.state==CRSF_WRITE_IDLE); /* Classification is not UART acceptance. */
    send_command(1,100);assert(p.report.state==CRSF_WRITE_WAIT && !allowed(1));
    uint8_t confirm[sizeof(field)];memcpy(confirm,field,sizeof(field));confirm[7]=3;
    reply(confirm,sizeof(confirm),0,110);assert(allowed(4) && allowed(5) && allowed(6));
    crsf_tools_tick(&p,5000);assert(p.report.state==CRSF_WRITE_WAIT); /* Human confirmation is not a 3s deadline. */
    send_command(4,5001);assert(!allowed(4));
    uint8_t running[sizeof(field)];memcpy(running,field,sizeof(field));running[7]=2;
    reply(running,6,1,5002);read_field(1,5003);reply(running+6,sizeof(running)-6,0,5004);
    assert(!allowed(4) && allowed(5) && allowed(6));
    send_command(6,5100);reply(running,sizeof(running),0,5101);
    send_command(5,5200);assert(!allowed(4));reply(field,sizeof(field),0,5201);
    assert(p.report.state==CRSF_WRITE_CANCELLED && !p.report.verified);
    assert(allowed(1));send_command(1,5300);reply(running,sizeof(running),0,5301);
    send_command(6,5400);reply(field,sizeof(field),0,5401);
    assert(p.report.state==CRSF_COMMAND_COMPLETE && !p.report.verified);
    /* Silent device / stale responses cannot be reported as completion. */
    send_command(1,6000);send_command(6,8000);crsf_tools_tick(&p,9001);
    assert(p.report.state==CRSF_WRITE_TIMEOUT);reply(field,sizeof(field),0,9002);
    assert(p.report.state==CRSF_WRITE_TIMEOUT);
    load(10000);send_command(1,10100);crsf_tools_cancel(&p);reply(running,sizeof(running),0,10101);
    assert(p.report.state==CRSF_WRITE_CANCELLED && !allowed(6));
    load(11000);send_command(1,11100);confirm[2]='X';reply(confirm,sizeof(confirm),0,11101);
    assert(p.report.state==CRSF_WRITE_MISMATCH && !allowed(4));
    /* Hidden, truncated, invalid-status and disabled commands stay blocked. */
    crsf_tools_init(&p,1);uint8_t bad[sizeof(field)];memcpy(bad,field,sizeof(field));bad[1]|=128;
    read_field(0,0);reply(bad,sizeof(bad),0,1);assert(!allowed(1));
    read_field(0,2);reply(field,sizeof(field)-1,0,3);assert(!allowed(1));
    memcpy(bad,field,sizeof(field));bad[7]=6;read_field(0,4);reply(bad,sizeof(bad),0,5);assert(!allowed(1));
    crsf_tools_init(&p,0);load(10);assert(!allowed(1));
    crsf_tools_init(&p,1);load(20);send_command(1,UINT32_MAX-50);crsf_tools_tick(&p,2950);
    assert(p.report.state==CRSF_WRITE_TIMEOUT);
    puts("CRSF command metadata/start/confirm/query/cancel/timeout/schema/wrap PASS");
}
