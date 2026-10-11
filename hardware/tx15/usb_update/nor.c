/* No status writes, chip erase, internal Flash or option-byte operations. */
#include "nor.h"
#include "nor_geometry.h"
#include <string.h>
#ifndef TX15_READ32
#define TX15_READ32(a) (*(volatile uint32_t *)(uintptr_t)(a))
#define TX15_WRITE32(a,v) (*(volatile uint32_t *)(uintptr_t)(a)=(v))
#define TX15_READ8(a) (*(volatile uint8_t *)(uintptr_t)(a))
#define TX15_WRITE8(a,v) (*(volatile uint8_t *)(uintptr_t)(a)=(v))
#endif
#define QSPI 0x52005000u
static int controller(void)
{
    return (TX15_READ32(0x580244d4u)&0x4000u)
        && TX15_READ32(QSPI)==0x0f000001u && TX15_READ32(QSPI+4)==0x00170300u;
}
static void service(struct tx15_update_nor *n)
{ if(n->service)n->service(n->ctx); }
static int wait(struct tx15_update_nor *n,unsigned condition)
{
    for(uint32_t i=0;i<n->budget;i++) {
        uint32_t sr=TX15_READ32(QSPI+8);
        if(sr&0x11u)return 0;
        if(condition==0 && !(sr&0x20u))return 1;
        if(condition==1 && (sr&0x3f00u))return 1;
        if(condition==2 && (sr&0x22u)==2u)return 1;
        if(condition==3 && (sr&4u))return 1;
        if((i&127u)==127u)service(n);
    }
    return 0;
}
static int command(struct tx15_update_nor *n,unsigned op,uint32_t address,
                   uint8_t *read,const uint8_t *write,size_t bytes)
{
    if(!controller() || !wait(n,0))return 0;
    TX15_WRITE32(QSPI+12,0x1bu);
    if(bytes)TX15_WRITE32(QSPI+16,(uint32_t)bytes-1);
    unsigned addressed=op==3||op==0x5a||op==0x20||op==2;
    uint32_t ccr=op|0x100u|(addressed?0x2400u:0);
    if(bytes)ccr|=0x01000000u;
    if(read)ccr|=0x04000000u;
    if(op==0x5a)ccr|=8u<<18;
    TX15_WRITE32(QSPI+20,ccr);
    if(addressed)TX15_WRITE32(QSPI+24,address);
    for(size_t i=0;i<bytes;i++) {
        if(!wait(n,read?1:3))return 0;
        if(read)read[i]=TX15_READ8(QSPI+32);
        else TX15_WRITE8(QSPI+32,write[i]);
        if((i&127u)==127u)service(n);
    }
    if(!wait(n,2))return 0;
    TX15_WRITE32(QSPI+12,0x1bu);return 1;
}
static int status(struct tx15_update_nor *n,uint8_t s[3])
{
    static const unsigned ops[]={5,0x35,0x15};
    for(unsigned i=0;i<3;i++)if(!command(n,ops[i],0,&s[i],0,1))return 0;
    return 1;
}
static int observe(struct tx15_update_nor *n,struct tx15_update_flash_info *info)
{
    uint8_t id[3],s[3],sfdp[1024];
    memset(info,0,sizeof(*info));
    if(!command(n,0x9f,0,id,0,3) || !status(n,s)
        || !command(n,0x5a,0,sfdp,0,sizeof(sfdp)))return 0;
    return tx15_update_nor_assess((uint32_t)id[0]<<16|(uint32_t)id[1]<<8|id[2],s,sfdp,sizeof(sfdp),info);
}
static int enter(struct tx15_update_nor *n)
{
    if(!n || !n->ready || n->active)return 0;
    n->active=1;return 1;
}
static int leave(struct tx15_update_nor *n,int ok)
{
    n->active=0;if(!ok)n->ready=0;return ok;
}
int tx15_update_nor_init(struct tx15_update_nor *n,void(*poll)(void*),uint32_t(*ms)(void*),void *ctx,uint32_t budget)
{
    if(!n || !budget)return 0;
    memset(n,0,sizeof(*n));n->service=poll;n->ms=ms;n->ctx=ctx;n->budget=budget;n->active=1;
    struct tx15_update_flash_info info;
    int ok=observe(n,&info);n->active=0;n->ready=!!ok;return ok;
}
int tx15_update_nor_observe(void *ctx,struct tx15_update_flash_info *info)
{
    struct tx15_update_nor *n=ctx;
    if(!info)return 0;
    memset(info,0,sizeof(*info));
    if(!enter(n))return 0;
    return leave(n,observe(n,info));
}
int tx15_update_nor_read(void *ctx,uint32_t offset,uint8_t *dst,size_t bytes)
{
    struct tx15_update_nor *n=ctx;
    if(!dst || !bytes || offset>=0x100000u || bytes>0x100000u-offset || !enter(n))return 0;
    return leave(n,command(n,3,offset,dst,0,bytes));
}
static int writable(struct tx15_update_nor *n)
{
    uint8_t s[3];
    struct tx15_update_flash_info info={0xc84018u,0x1000000u,256,4096,0,0,0,1};
    if(!status(n,s))return 0;
    info.sr1=s[0];info.sr2=s[1];info.sr3=s[2];
    if(!tx15_update_flash_writable(&info) || !command(n,6,0,0,0,0))return 0;
    if(!command(n,5,0,s,0,1))return 0;
    return s[0]==2; /* WEL, no WIP/protection changes. */
}
static int finish(struct tx15_update_nor *n,uint32_t deadline)
{
    uint32_t start=n->ms?n->ms(n->ctx):0;
    for(uint32_t i=0;i<n->budget;i++) {
        uint8_t s=0;
        if(!command(n,5,0,&s,0,1))return 0;
        if(!(s&1u))return s==0; /* WEL clears when command completes. */
        service(n);
        if(n->ms && (uint32_t)(n->ms(n->ctx)-start)>=deadline)return 0;
    }
    return 0;
}
int tx15_update_nor_erase4k(void *ctx,uint32_t offset)
{
    struct tx15_update_nor *n=ctx;
    if(offset>=0xf0000u || offset%4096u || !enter(n))return 0;
    return leave(n,writable(n) && command(n,0x20,offset,0,0,0) && finish(n,5000));
}
int tx15_update_nor_program(void *ctx,uint32_t offset,const uint8_t *src,size_t bytes)
{
    struct tx15_update_nor *n=ctx;
    if(!src || !bytes || offset>=0xf0000u || bytes>0xf0000u-offset
        || bytes>256u-offset%256u || !enter(n))return 0;
    return leave(n,writable(n) && command(n,2,offset,0,src,bytes) && finish(n,100));
}
