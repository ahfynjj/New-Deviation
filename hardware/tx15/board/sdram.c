/* New Deviation TX15 bring-up; GPL-3.0-or-later. */
#include "sdram.h"
#ifndef TX15_READ32
#define TX15_READ32(a) (*(volatile uint32_t *)(a))
#define TX15_WRITE32(a,v) (*(volatile uint32_t *)(a) = (v))
#endif
#ifndef TX15_SDRAM_DELAY
static void delay(uint32_t cycles) {
    for (volatile uint32_t i=0; i<cycles; ++i) __asm volatile("nop");
}
#define TX15_SDRAM_DELAY(n) delay(n)
#endif
#ifndef TX15_SDRAM_BARRIER
#define TX15_SDRAM_BARRIER() __asm volatile("dsb" ::: "memory")
#endif
#define AHB3 0x580244d4u
#define AHB4 0x580244e0u
#define BCR 0x52004000u
#define SDCR1 0x52004140u
#define SDCR2 0x52004144u
#define SDTR1 0x52004148u
#define SDTR2 0x5200414cu
#define CMD 0x52004150u
#define REFRESH 0x52004154u
#define STATUS 0x52004158u

static void modify(uint32_t a, uint32_t mask, uint32_t value) {
    TX15_WRITE32(a, (TX15_READ32(a) & ~mask) | value);
}
static int check(volatile struct tx15_sdram_report *r, uint32_t a, uint32_t expected) {
    uint32_t actual=TX15_READ32(a);
    if(actual!=expected) {
        r->bad_address=a; r->expected=expected; r->actual=actual; r->error=3;
        return 1;
    }
    r->checks++;
    return 0;
}
int tx15_sdram_test(volatile struct tx15_sdram_report *r) {
    r->state=1;
    if ((TX15_READ32(0x58024400u)&0x3f0f001du)!=0x3030005u
        || (TX15_READ32(0x58024410u)&0x3fu)!=0x1bu
        || (TX15_READ32(0x58024418u)&0xf7fu)!=0x48u
        || (TX15_READ32(0x58024428u)&0x3f3u)!=0xc2u
        || (TX15_READ32(0x5802442cu)&0x7000fu)!=0x10008u
        || (TX15_READ32(0x58024430u)&0xffffu)!=0x23fu
        || (TX15_READ32(0x5802444cu)&3u) || (TX15_READ32(AHB3)&0x1000u)
        || (TX15_READ32(0xe000ed14u)&0x30000u) || (TX15_READ32(0xe000ed94u)&1u)) {
        r->error=1; return 1;
    }
    TX15_WRITE32(AHB4, TX15_READ32(AHB4)|0xfcu);
    (void)TX15_READ32(AHB4);
    /* C0; D0,1,8,9,10,14,15; E0,1,7..15; F0..5,11..15;
     * G0,1,4,5,8,15; H6,7. PH12 and all other pins are preserved. */
    static const uint16_t pins[]={0x0001,0xc703,0xff83,0xf83f,0x8133,0x00c0};
    for(unsigned port=0;port<6;port++) for(unsigned pin=0;pin<16;pin++) {
        if(!(pins[port]&(1u<<pin))) continue;
        uint32_t base=0x58020800u+port*0x400u, shift=2u*pin;
        modify(base+0x20u+(pin/8u)*4u,15u<<((pin%8u)*4u),12u<<((pin%8u)*4u));
        modify(base+4u,1u<<pin,0);
        modify(base+8u,3u<<shift,3u<<shift);
        modify(base+12u,3u<<shift,0);
        modify(base,3u<<shift,2u<<shift);
    }
    TX15_WRITE32(AHB3,TX15_READ32(AHB3)|0x1000u);
    (void)TX15_READ32(AHB3);
    /* FMC kernel HCLK64 / 2 -> SDRAM32, CAS3, 8 columns/12 rows/4 banks/x16.
     * Cycles: TMRD2 TXSR8 TRAS4 TRC8 TWR6 TRP4 TRCD4, deliberately relaxed.
     * TRC/TRP are shared through bank1 even when targeting bank2. */
    modify(SDCR1,0x7c00u,0x1800u);
    modify(SDCR2,0x7fffu,0x1d4u);
    modify(SDTR1,0xf0f000u,0x307000u);
    modify(SDTR2,0xfffffffu,0x3050371u);
    r->sdcr1=TX15_READ32(SDCR1); r->sdcr2=TX15_READ32(SDCR2);
    r->sdtr1=TX15_READ32(SDTR1); r->sdtr2=TX15_READ32(SDTR2);
    if ((r->sdcr1&0x7c00u)!=0x1800u || (r->sdcr2&0x7fffu)!=0x1d4u
        || (r->sdtr1&0xf0f000u)!=0x307000u || (r->sdtr2&0xfffffffu)!=0x3050371u) {
        r->error=2; return 1;
    }
    modify(BCR,0x80000001u,0x80000000u); /* enable FMC, disable unused async bank1 */
    TX15_WRITE32(CMD,9u); /* bank2 clock enable */
    TX15_SDRAM_DELAY(128000u); /* >=1ms at core128, exceeds >=100us */
    TX15_WRITE32(CMD,10u); /* precharge all */
    TX15_SDRAM_DELAY(12800u);
    TX15_WRITE32(CMD,0xebu); /* eight auto-refresh cycles */
    TX15_SDRAM_DELAY(12800u);
    TX15_WRITE32(CMD,0x4620cu); /* mode 0x231: BL2/CAS3/single write */
    TX15_SDRAM_DELAY(12800u);
    /* Conservative 7.8125us refresh: 32MHz*7.8125us - 20 = 230. */
    TX15_WRITE32(REFRESH,460u);
    r->sdrtr=TX15_READ32(REFRESH);
    if(r->sdrtr!=460u || (TX15_READ32(STATUS)&0x19u)) { r->error=2; return 1; }
    r->state=2;
    for(unsigned bit=0;bit<32;bit++) {
        TX15_WRITE32(0xd0000000u,1u<<bit); TX15_SDRAM_BARRIER();
        if(check(r,0xd0000000u,1u<<bit)) return 1;
    }
    for(unsigned pass=0;pass<2;pass++) {
        for(unsigned i=0;i<16384;i++) TX15_WRITE32(0xd0000000u+i*4u,(0xa5a50000u^i)^(pass?0xffffffffu:0));
        TX15_SDRAM_BARRIER();
        TX15_SDRAM_DELAY(128000u);
        for(unsigned i=0;i<16384;i++) if(check(r,0xd0000000u+i*4u,(0xa5a50000u^i)^(pass?0xffffffffu:0))) return 1;
    }
    if(TX15_READ32(STATUS)&0x19u) { r->error=4; return 1; }
    r->words=16384; r->state=3;
    return 0;
}
