/* New Deviation TX15 MAX board support; GPL-3.0-or-later.
 * Register facts: ST RM0433. Board mapping and bench evidence: power-notes.md.
 */
#include "power.h"

#ifndef TX15_READ32
#define TX15_READ32(address) (*(volatile uint32_t *)(uintptr_t)(address))
#endif
#ifndef TX15_WRITE32
#define TX15_WRITE32(address, value) \
    (*(volatile uint32_t *)(uintptr_t)(address) = (value))
#endif

#define RCC_AHB4ENR 0x580244e0u
#define GPIOA 0x58020000u
#define GPIOH 0x58021c00u
#define MODER 0x00u
#define OTYPER 0x04u
#define OSPEEDR 0x08u
#define PUPDR 0x0cu
#define IDR 0x10u
#define ODR 0x14u
#define BSRR 0x18u

void tx15_power_init(void)
{
    TX15_WRITE32(RCC_AHB4ENR, TX15_READ32(RCC_AHB4ENR) | 0x81u);
    (void)TX15_READ32(RCC_AHB4ENR); /* Clock enable propagation before GPIO. */

    /* Preload high before selecting output mode: no low pulse on power hold. */
    TX15_WRITE32(GPIOH + BSRR, 1u << 12);
    TX15_WRITE32(GPIOH + OTYPER, TX15_READ32(GPIOH + OTYPER) & ~(1u << 12));
    TX15_WRITE32(GPIOH + OSPEEDR, TX15_READ32(GPIOH + OSPEEDR) & ~(3u << 24));
    TX15_WRITE32(GPIOH + PUPDR, TX15_READ32(GPIOH + PUPDR) & ~(3u << 24));
    TX15_WRITE32(GPIOH + MODER,
                 (TX15_READ32(GPIOH + MODER) & ~(3u << 24)) | (1u << 24));

    TX15_WRITE32(GPIOA + PUPDR,
                 (TX15_READ32(GPIOA + PUPDR) & ~(3u << 8)) | (1u << 8));
    TX15_WRITE32(GPIOA + MODER, TX15_READ32(GPIOA + MODER) & ~(3u << 8));
}

uint32_t tx15_power_status(void)
{
    uint32_t status = 0;
    if ((TX15_READ32(RCC_AHB4ENR) & 0x81u) != 0x81u)
        return 0;
    if (((TX15_READ32(GPIOH + MODER) >> 24) & 3u) == 1u &&
        !(TX15_READ32(GPIOH + OTYPER) & (1u << 12)))
        status |= TX15_HOLD_OUTPUT;
    if (TX15_READ32(GPIOH + ODR) & (1u << 12)) status |= TX15_HOLD_LATCH_HIGH;
    if (TX15_READ32(GPIOH + IDR) & (1u << 12)) status |= TX15_HOLD_PIN_HIGH;
    if (!(TX15_READ32(GPIOA + MODER) & (3u << 8)) &&
        ((TX15_READ32(GPIOA + PUPDR) >> 8) & 3u) == 1u) {
        status |= TX15_BUTTON_INPUT;
        if (!(TX15_READ32(GPIOA + IDR) & (1u << 4))) status |= TX15_BUTTON_PRESSED;
    }
    return status;
}
