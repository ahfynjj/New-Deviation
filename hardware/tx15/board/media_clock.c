#include <stdint.h>
#include "media_clock.h"
#ifndef TX15_READ32
#define TX15_READ32(a) (*(volatile uint32_t *)(a))
#define TX15_WRITE32(a,v) (*(volatile uint32_t *)(a)=(v))
#endif
#define MEDIA_RCC 0x58024400u
static unsigned media_owned;
static void clock_modify(uint32_t offset,uint32_t mask,uint32_t value) {
    uint32_t a=MEDIA_RCC+offset;TX15_WRITE32(a,(TX15_READ32(a)&~mask)|value);
}
static int core_profile(void) {
    return (TX15_READ32(MEDIA_RCC)&0x03030000u)==0x03030000u
        && (TX15_READ32(MEDIA_RCC+0x10)&0x3f)==0x1b
        && (TX15_READ32(MEDIA_RCC+0x18)&0xf7f)==0x48
        && (TX15_READ32(MEDIA_RCC+0x28)&0x3f3)==0xc2
        && (TX15_READ32(MEDIA_RCC+0x2c)&0x7000f)==0x10008
        && (TX15_READ32(MEDIA_RCC+0x30)&0x7fffff)==0x01023f;
}
static int media_profile(void) {
    return core_profile() && (TX15_READ32(MEDIA_RCC+0x28)&0x3f000)==0xc000
        && (TX15_READ32(MEDIA_RCC+0x2c)&0x3800f0)==0x280090
        && TX15_READ32(MEDIA_RCC+0x38)==0x01010e61
        && (TX15_READ32(MEDIA_RCC+0x3c)&0xfff8)==(2490u<<3)
        && (TX15_READ32(MEDIA_RCC)&(1u<<26));
}
int tx15_media_clock_init(void) {
    if(media_owned)return media_profile()?0:-1;
    if(!core_profile() || (TX15_READ32(MEDIA_RCC)&0x0c000000u))return -1;
    /* Set every output while PLL2 is OFF. Never edit a live PLL's gates.
     * HSE48/M12*(98+2490/8192) /P8=49.15198MHz; /R2=196.60791MHz. */
    clock_modify(0x28,0x3f000,12u<<12);
    clock_modify(0x2c,0x3800f0,0x280080);
    TX15_WRITE32(MEDIA_RCC+0x38,0x01010e61);
    TX15_WRITE32(MEDIA_RCC+0x3c,2490u<<3);
    clock_modify(0x2c,0,1u<<4);
    clock_modify(0,0,1u<<26);media_owned=1;
    return media_profile()?0:-1;
}
int tx15_media_clock_ready(void) {
    if(!media_owned || !media_profile())return -1;
    return (TX15_READ32(MEDIA_RCC)&(1u<<27))?1:0;
}
