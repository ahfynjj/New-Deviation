/* Register definitions checked against ST CMSIS H750 v1.10.3/RM0433.
 * New Deviation TX15 USB support; GPL-3.0-or-later. */
#include "usb_hw.h"
#ifndef TX15_READ32
#define TX15_READ32(a) (*(volatile uint32_t *)(uintptr_t)(a))
#define TX15_WRITE32(a,v) (*(volatile uint32_t *)(uintptr_t)(a)=(v))
#endif
static void setbits(uint32_t a,uint32_t bits)
{ TX15_WRITE32(a,TX15_READ32(a)|bits);(void)TX15_READ32(a); }
static int waitbits(uint32_t a,uint32_t bits,uint32_t budget)
{ while (budget--) if ((TX15_READ32(a)&bits)==bits) return 1;return 0; }
static void output_low(uint32_t gpio,unsigned pin)
{
    TX15_WRITE32(gpio+0x18,1u<<(pin+16));
    TX15_WRITE32(gpio+4,TX15_READ32(gpio+4)&~(1u<<pin));
    TX15_WRITE32(gpio+0x0c,TX15_READ32(gpio+0x0c)&~(3u<<(pin*2)));
    TX15_WRITE32(gpio,(TX15_READ32(gpio)&~(3u<<(pin*2)))|(1u<<(pin*2)));
}
int tx15_usb_hw_init(uint32_t budget)
{
    if (!budget) return -1;
    setbits(0x580244e0u,0x8bu); /* GPIO A/B/D/H; no PH12 changes. */
    output_low(0x58020400u,13); output_low(0x58020c00u,4);
    TX15_WRITE32(0x58020000u,(TX15_READ32(0x58020000u)&~(15u<<22))|(10u<<22));
    TX15_WRITE32(0x58020004u,TX15_READ32(0x58020004u)&~(3u<<11));
    TX15_WRITE32(0x58020008u,TX15_READ32(0x58020008u)|(15u<<22));
    TX15_WRITE32(0x5802000cu,TX15_READ32(0x5802000cu)&~(15u<<22));
    TX15_WRITE32(0x58020024u,(TX15_READ32(0x58020024u)&~(255u<<12))|(0xaau<<12));
    TX15_WRITE32(0x58021c00u,TX15_READ32(0x58021c00u)&~(3u<<10));
    TX15_WRITE32(0x58021c0cu,TX15_READ32(0x58021c0cu)&~(3u<<10)); /* PH5 external VBUS. */
    setbits(0x58024400u,1u<<12); /* H750 HSI48 lives in RCC_CR, not CRRCR. */
    if (!waitbits(0x58024400u,1u<<13,budget)) return -2;
    uint32_t select=TX15_READ32(0x58024454u);
    TX15_WRITE32(0x58024454u,(select&~((3u<<20)|(3u<<8)))|(3u<<20)); /* USB=HSI48, RNG=HSI48. */
    setbits(0x580244f4u,1u<<28); /* PWR clock. Preserve LDO/Run* supply configuration. */
    setbits(0x5802480cu,1u<<24); /* Existing VDD33_USB rail, voltage detector. */
    if (!waitbits(0x5802480cu,1u<<26,budget)) return -3;
    setbits(0x580244ecu,2u); /* CRS */
    TX15_WRITE32(0x40008400u,0x20u<<8); /* default HSI48 trim, counter off */
    /* ST HAL documents USB2 SOF source 0 on revisions <=Y, 3 on newer H750. */
    uint32_t source=(TX15_READ32(0x5c001000u)>>16)<=0x2001u?0u:3u;
    TX15_WRITE32(0x40008404u,(source<<28)|(34u<<16)|47999u);
    TX15_WRITE32(0x4000840cu,0xfu);
    setbits(0x40008400u,0x60u);
    setbits(0x580244dcu,1u<<6); /* RNG */
    setbits(0x580244d8u,1u<<27); /* OTG_FS */
    return 0;
}
int tx15_usb_hw_session(uint64_t *session,uint32_t budget)
{
    if (!session) return -1;
    *session=0;
    if (!budget || !(TX15_READ32(0x58024400u)&0x2000u)) return -1;
    TX15_WRITE32(0x48021800u,4u);
    uint32_t values[2];
    for (unsigned i=0;i<2;i++) {
        unsigned ready=0;
        while (budget) {
            budget--;
            uint32_t sr=TX15_READ32(0x48021804u);
            if (sr&0x66u) return -2; /* current and latched seed/clock errors */
            if (sr&1u) { values[i]=TX15_READ32(0x48021808u);ready=1;break; }
        }
        if (!ready) return -3;
    }
    uint64_t value=(uint64_t)values[0]|(uint64_t)values[1]<<32;
    if (!value) return -4;
    *session=value;return 0;
}
int tx15_usb_hw_vbus(void) { return !!(TX15_READ32(0x58021c10u)&0x20u); }
int tx15_usb_hw_sync(void)
{
    uint32_t status=TX15_READ32(0x40008408u);
    TX15_WRITE32(0x4000840cu,0xfu);
    return status&4u?-1:status&1u?1:0;
}
void tx15_usb_hw_uid(uint8_t out[12])
{
    for (unsigned i=0;i<3;i++) {
        uint32_t v=TX15_READ32(0x1ff1e800u+i*4);
        for (unsigned j=0;j<4;j++) out[i*4+j]=(uint8_t)(v>>(j*8));
    }
}
