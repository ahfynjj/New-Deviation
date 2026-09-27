/* New Deviation TX15 MAX board support; GPL-3.0-or-later. */
#include "clock.h"
#ifndef TX15_READ32
#define TX15_READ32(a) (*(volatile uint32_t *)(a))
#define TX15_WRITE32(a, v) (*(volatile uint32_t *)(a) = (v))
#endif
#define RCC_CR 0x58024400u
#define RCC_CFGR 0x58024410u
#define RCC_D1CFGR 0x58024418u

enum tx15_clock_result tx15_clock_hse_init(uint32_t budget)
{
    uint32_t cr = TX15_READ32(RCC_CR);
    /* HSI64 ready, no HSE/bypass/CSS or PLL already active. */
    if (!budget || (cr & 0x1du) != 5u || (cr & 0x3f0f0000u)
            || (TX15_READ32(RCC_CFGR) & 0x3fu)
            || (TX15_READ32(RCC_D1CFGR) & 0xf0fu))
        return TX15_CLOCK_BAD_STATE;
    TX15_WRITE32(RCC_CR, cr | (1u << 16));
    uint32_t remaining = budget;
    while (!(TX15_READ32(RCC_CR) & (1u << 17))) {
        if (!--remaining) return TX15_CLOCK_HSE_TIMEOUT;
    }
    TX15_WRITE32(RCC_CFGR, (TX15_READ32(RCC_CFGR) & ~7u) | 2u);
    remaining = budget;
    while ((TX15_READ32(RCC_CFGR) & 0x38u) != 0x10u) {
        if (!--remaining) return TX15_CLOCK_SWITCH_TIMEOUT;
    }
    return TX15_CLOCK_OK;
}
