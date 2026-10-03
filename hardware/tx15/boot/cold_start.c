/* New Deviation native TX15 cold-start preparation; GPL-3.0-or-later.
 * Register and supply sequence: ST RM0433 and STM32H7 HAL PWREx documentation.
 */
#include "cold_start.h"
_Static_assert(TX15_CLOCK_BAD_STATE==1 && TX15_CLOCK_SUPPLY_TIMEOUT==5,"early_supply.S return ABI");
#ifndef TX15_READ32
#define TX15_READ32(a) (*(volatile uint32_t *)(a))
#define TX15_WRITE32(a,v) (*(volatile uint32_t *)(a)=(v))
#endif
#define BOOT_SUPPLY 0x5802480cu
#define BOOT_VOS 0x58024818u
#define BOOT_ACTUAL 0x58024804u
#define BOOT_FLASH 0x52002000u
static int wait_bits(uint32_t address,uint32_t mask,uint32_t value,uint32_t budget)
{
    while (budget--) if ((TX15_READ32(address)&mask)==value) return 1;
    return 0;
}
enum tx15_clock_result tx15_boot_clock_init(uint32_t budget)
{
    uint32_t cr=TX15_READ32(0x58024400u), supply=TX15_READ32(BOOT_SUPPLY);
    uint32_t latency=TX15_READ32(BOOT_FLASH)&15u;
    /* Only from reset clocks. Do not alter live firmware supply/Flash/QSPI. */
    if (!budget || (cr&0x1du)!=5u || (cr&0x3f0f0000u)
            || (TX15_READ32(0x58024410u)&0x3fu)
            || (TX15_READ32(0x58024418u)&0xf7fu)
            || (TX15_READ32(0x5802441cu)&0x770u)
            || (TX15_READ32(0x58024420u)&0x70u)
            || (TX15_READ32(0xe000ed14u)&0x30000u)
            || (TX15_READ32(0xe000ed94u)&1u)
            || (supply&7u)!=2u || !(TX15_READ32(BOOT_ACTUAL)&0x2000u) || latency>7u)
        return TX15_CLOCK_BAD_STATE;
    /* SCUEN must already be finalized by stackless early_supply.S, before
     * startup's first RAM/stack write. This C stage never finalizes supply. */
    TX15_WRITE32(BOOT_VOS,(TX15_READ32(BOOT_VOS)&~0xc000u)|0xc000u);
    if (!wait_bits(BOOT_VOS,0xe000u,0xe000u,budget)
            || !wait_bits(BOOT_ACTUAL,0xe000u,0xe000u,budget))
        return TX15_CLOCK_VOLTAGE_TIMEOUT;
    /* Conservative read latency for the fixed 64 MHz HCLK. Preserve a larger
     * existing latency and programming-frequency/cache-related ACR bits. */
    if (latency<2u) TX15_WRITE32(BOOT_FLASH,(TX15_READ32(BOOT_FLASH)&~15u)|2u);
    if (!wait_bits(BOOT_FLASH,15u,latency<2u?2u:latency,budget))
        return TX15_CLOCK_FLASH_TIMEOUT;
    enum tx15_clock_result result=tx15_clock_hse_init(budget);
    if (result!=TX15_CLOCK_OK) return result;
    return tx15_clock_pll128_init(budget);
}
