/* New Deviation TX15 MAX board support; GPL-3.0-or-later. */
#include "clock.h"
#ifndef TX15_READ32
#define TX15_READ32(a) (*(volatile uint32_t *)(a))
#define TX15_WRITE32(a,v) (*(volatile uint32_t *)(a) = (v))
#endif
#define CR 0x58024400u
#define CFGR 0x58024410u
#define D1 0x58024418u
#define D2 0x5802441cu
#define D3 0x58024420u
#define SEL 0x58024428u
#define CFG 0x5802442cu
#define DIV 0x58024430u

enum tx15_clock_result tx15_clock_pll128_init(uint32_t budget)
{
    uint32_t cr = TX15_READ32(CR);
    uint32_t power = TX15_READ32(0x58024804u);
    uint32_t latency = TX15_READ32(0x52002000u) & 15u;
    if (!budget || (cr & 0x3001du) != 0x30005u || (cr & 0x3f0c0000u)
            || (TX15_READ32(CFGR) & 0x3fu) != 0x12u
            || (TX15_READ32(D1) & 0xf7fu) || (TX15_READ32(D2) & 0x770u)
            || (TX15_READ32(D3) & 0x70u) || !(power & 0x2000u)
            || !(power & 0xc000u) || (TX15_READ32(0x5802480cu) & 3u) != 2u
            || latency < 1u || latency > 7u)
        return TX15_CLOCK_BAD_STATE;

    /* HSE 48 / M12 = 4 MHz; wide VCO * N64 = 256 MHz; P2 = 128 MHz.
     * PLL1 fractional mode and Q/R outputs disabled; PLL2/3 unchanged/off. */
    TX15_WRITE32(SEL, (TX15_READ32(SEL) & ~0x3f3u) | 0xc2u);
    TX15_WRITE32(CFG, (TX15_READ32(CFG) & ~0x7000fu) | 0x10008u);
    TX15_WRITE32(DIV, (TX15_READ32(DIV) & ~0xffffu) | 0x23fu);
    if ((TX15_READ32(SEL) & 0x3f3u) != 0xc2u || (TX15_READ32(CFG) & 0x7000fu) != 0x10008u
            || (TX15_READ32(DIV) & 0xffffu) != 0x23fu)
        return TX15_CLOCK_BAD_STATE;
    TX15_WRITE32(CR, cr | (1u << 24));
    uint32_t remaining = budget;
    while (!(TX15_READ32(CR) & (1u << 25))) {
        if (!--remaining) return TX15_CLOCK_PLL_TIMEOUT;
    }
    /* Install bus dividers before selecting the faster source. */
    TX15_WRITE32(D1, (TX15_READ32(D1) & ~0xf7fu) | 0x48u);
    TX15_WRITE32(D2, (TX15_READ32(D2) & ~0x770u) | 0x440u);
    TX15_WRITE32(D3, (TX15_READ32(D3) & ~0x70u) | 0x40u);
    if ((TX15_READ32(D1) & 0xf7fu) != 0x48u || (TX15_READ32(D2) & 0x770u) != 0x440u
            || (TX15_READ32(D3) & 0x70u) != 0x40u)
        return TX15_CLOCK_BAD_STATE;
    TX15_WRITE32(CFGR, (TX15_READ32(CFGR) & ~7u) | 3u);
    remaining = budget;
    while ((TX15_READ32(CFGR) & 0x38u) != 0x18u) {
        if (!--remaining) return TX15_CLOCK_SWITCH_TIMEOUT;
    }
    return TX15_CLOCK_OK;
}
