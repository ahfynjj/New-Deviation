/* Independent SDMMC1 command/IDMA reader, 1-bit/400kHz.
 * ST stm32h750xx.h and ST HAL SD v1.11.2 register/sequence facts;
 * target pin reference in storage-notes.md. GPL-3.0-or-later. */
#include "storage.h"
#include "media_clock.h"
#ifndef TX15_READ32
#define TX15_READ32(a) (*(volatile uint32_t *)(a))
#define TX15_WRITE32(a,v) (*(volatile uint32_t *)(a)=(v))
#endif
#ifndef TX15_STORAGE_DMA_ADDRESS
#define TX15_STORAGE_DMA_ADDRESS(p) ((uint32_t)(uintptr_t)(p))
#endif
#ifndef TX15_STORAGE_BARRIER
#define TX15_STORAGE_BARRIER() __asm volatile("dsb" ::: "memory")
#endif
#define R(a) TX15_READ32(a)
#define W(a,v) TX15_WRITE32(a,v)
#define RCC 0x58024400u
#define SD 0x52007000u
#define CMD_FLAGS 0x002000c5u
#define DATA_FLAGS 0x18000f3au
static uint32_t dma_buffer[128] __attribute__((aligned(32)));
static unsigned owned,command_pending,read_pending,last_command,response_kind;
static uint32_t saved_selector,c_gpio[5],d_gpio[5];
volatile struct tx15_storage_hw_report tx15_storage_hw_report;
static void snapshot(void) {
    tx15_storage_hw_report.status=R(SD+0x34);
    tx15_storage_hw_report.clkcr=R(SD+4);tx15_storage_hw_report.power=R(SD);
    tx15_storage_hw_report.cmd=R(SD+0xc);
    tx15_storage_hw_report.pllcfgr=R(RCC+0x2c);tx15_storage_hw_report.selector=R(RCC+0x4c);
}
static void modify(uint32_t a,uint32_t mask,uint32_t value) {W(a,(R(a)&~mask)|value);}
static void pins(uint32_t port,unsigned first,unsigned last,uint32_t *saved,int restore) {
    const unsigned offsets[]={0,4,8,12,first>=8?0x24:0x20};
    uint32_t mask=0,mode=0,afmask=0,af=0,bits=0,pull=0;
    for(unsigned i=first;i<=last;i++) {
        bits|=1u<<i;mask|=3u<<(i*2);mode|=2u<<(i*2);
        afmask|=15u<<((i%8)*4);af|=12u<<((i%8)*4);
        if(i!=12)pull|=1u<<(i*2);
    }
    const uint32_t masks[]={mask,bits,mask,mask,afmask};
    const uint32_t values[]={mode,0,mask,pull,af};
    for(unsigned i=0;i<5;i++) {
        uint32_t address=port+offsets[i];
        if(!restore)saved[i]=R(address);
        modify(address,masks[i],restore?saved[i]&masks[i]:values[i]);
    }
}
static void stop(void *ctx) {
    (void)ctx;if(!owned)return;
    /* Preserve active timeout state; completed responses were already captured
     * before their W1C flags were cleared by response()/read_poll(). */
    if(command_pending || read_pending)snapshot();
    W(SD+0x3c,0);W(SD+0x50,0);W(SD+0x2c,0);W(SD+0xc,0);W(SD,0);
    modify(RCC+0x7c,0,1u<<16);modify(RCC+0x7c,1u<<16,0);
    modify(RCC+0xd4,1u<<16,0);(void)R(RCC+0xd4);
    pins(0x58020800u,8,12,c_gpio,1);pins(0x58020c00u,2,2,d_gpio,1);
    modify(RCC+0x4c,1u<<16,saved_selector);
    TX15_STORAGE_BARRIER();
    owned=command_pending=read_pending=0;
}
static int init(void *ctx) {
    (void)ctx;
    if(owned)return -1;
    tx15_storage_hw_report=(struct tx15_storage_hw_report){0};
    uint32_t address=TX15_STORAGE_DMA_ADDRESS(dma_buffer);
    int memory=(address>=0x24010000u && address<=0x2407be00u)
        || (address>=0x30000000u && address<=0x30047e00u);
    if(!memory || (address&31) || (R(0xe000ed14u)&0x30000u) || (R(0xe000ed94u)&1)
       || (R(RCC)&0x03030000u)!=0x03030000u || (R(RCC+0x10)&0x3f)!=0x1b
       || (R(RCC+0x18)&0xf7f)!=0x48 || (R(RCC+0x28)&0x3f3)!=0xc2
       || (R(RCC+0x30)&0x7fffff)!=0x01023f || (R(RCC+0x2c)&15)!=8
       || (R(RCC+0xd4)&(1u<<16)) || (R(RCC+0xdc)&(1u<<9))
       || (R(RCC+0x7c)&(1u<<16)) || (R(0xe000e104u)&(1u<<17))) {
        tx15_storage_hw_report.reason=1;return -1;
    }
    if(tx15_media_clock_ready()!=1) {tx15_storage_hw_report.reason=2;return -1;}
    saved_selector=R(RCC+0x4c)&(1u<<16);
    modify(RCC+0xe0,0,12);(void)R(RCC+0xe0);
    pins(0x58020800u,8,12,c_gpio,0);pins(0x58020c00u,2,2,d_gpio,0);
    /* Fixed media PLL2R is already enabled; never modify running PLL1. */
    modify(RCC+0x4c,1u<<16,1u<<16);
    modify(RCC+0xd4,0,1u<<16);(void)R(RCC+0xd4);
    modify(RCC+0x7c,0,1u<<16);modify(RCC+0x7c,1u<<16,0);
    W(SD+0x3c,0);W(SD+0x50,0);W(SD+0x2c,0);W(SD+0xc,0);
    W(SD+0x38,CMD_FLAGS|DATA_FLAGS);W(SD+4,TX15_MEDIA_SD_DIVIDER);W(SD,3);
    owned=1;command_pending=read_pending=0;return 0;
}
static int allowed(unsigned cmd,unsigned kind) {
    if(cmd==0)return kind==ND_SD_NONE;
    if(cmd==2 || cmd==9)return kind==ND_SD_LONG;
    if(cmd==41)return kind==ND_SD_OCR;
    return (cmd==3 || cmd==7 || cmd==8 || cmd==13 || cmd==16 || cmd==17 || cmd==55) && kind==ND_SD_SHORT;
}
static int command(void *ctx,unsigned cmd,uint32_t argument,unsigned kind) {
    (void)ctx;
    if(!allowed(cmd,kind) || !owned || command_pending || read_pending || (R(SD+0x34)&0x3000))return -1;
    W(SD+0x38,CMD_FLAGS);W(SD+8,argument);
    unsigned wait=kind==ND_SD_NONE?0:kind==ND_SD_LONG?0x300:0x100;
    W(SD+0xc,0x1000|wait|cmd|(cmd==17?64:0));
    last_command=cmd;response_kind=kind;command_pending=1;tx15_storage_hw_report.commands++;return 0;
}
static int response(void *ctx,uint32_t out[4]) {
    (void)ctx;if(!owned || !command_pending)return ND_SD_CRC;
    snapshot();uint32_t status=tx15_storage_hw_report.status;
    if(status&4) {W(SD+0x38,CMD_FLAGS);command_pending=0;return ND_SD_TIMEOUT;}
    if((status&1) && response_kind!=ND_SD_OCR) {W(SD+0x38,CMD_FLAGS);command_pending=0;return ND_SD_CRC;}
    /* Response flags may precede the tail of CPSM activity. Keep the same
     * request pending until idle, as required by the ST LL response helpers. */
    if(status&0x2000)return 0;
    unsigned done=response_kind==ND_SD_NONE?status&128:status&64;
    if(response_kind==ND_SD_OCR)done=status&65;
    if(!done)return 0;
    for(unsigned i=0;i<4;i++)out[i]=R(SD+0x14+i*4);
    tx15_storage_hw_report.response=out[0];
    int valid=response_kind!=ND_SD_SHORT || (R(SD+0x10)&63)==last_command;
    W(SD+0x38,CMD_FLAGS);command_pending=0;return valid?1:ND_SD_CRC;
}
static int read_start(void *ctx,uint32_t lba,int block_addressed) {
    if(!owned || command_pending || read_pending || (!block_addressed && lba>0x7fffffu))return -1;
    W(SD+0x50,0);W(SD+0x2c,0);W(SD+0x38,DATA_FLAGS);
    W(SD+0x24,8000000);W(SD+0x28,512);W(SD+0x2c,0x92); /* 512B receive, CMDTRANS starts DPSM. */
    TX15_STORAGE_BARRIER();W(SD+0x58,TX15_STORAGE_DMA_ADDRESS(dma_buffer));W(SD+0x50,1);
    if(command(ctx,17,block_addressed?lba:lba*512,ND_SD_SHORT)) {W(SD+0x50,0);W(SD+0x2c,0);return -1;}
    read_pending=1;tx15_storage_hw_report.reads++;return 0;
}
static int read_poll(void *ctx,uint8_t sector[512]) {
    if(!owned || !read_pending)return ND_SD_CRC;
    if(command_pending) {
        uint32_t r[4];int result=response(ctx,r);
        if(result<0) {read_pending=0;return result;} /* Keep terminal response snapshot. */
        if(!result)return 0;
        if(r[0]&0xfdffe008u)return ND_SD_CRC;
    }
    snapshot();uint32_t status=tx15_storage_hw_report.status;
    if(status&0x0800003au) {W(SD+0x50,0);W(SD+0x2c,0);read_pending=0;return ND_SD_CRC;}
    if(!(status&256) || R(SD+0x30) || (status&0x3000))return 0;
    W(SD+0x50,0);W(SD+0x2c,0);TX15_STORAGE_BARRIER();
    const volatile uint8_t *source=(const volatile uint8_t *)dma_buffer;
    for(unsigned i=0;i<512;i++)sector[i]=source[i];
    W(SD+0x38,DATA_FLAGS);read_pending=0;return 1;
}
const struct nd_sd_ops tx15_storage_ops={init,stop,command,response,read_start,read_poll};
