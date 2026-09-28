/* New Deviation TX15 bring-up; GPL-3.0-or-later. */
#ifndef TX15_SDRAM_H
#define TX15_SDRAM_H
#include <stdint.h>
struct tx15_sdram_report {
    uint32_t state, error, words, checks, bad_address, expected, actual;
    uint32_t sdcr1, sdcr2, sdtr1, sdtr2, sdrtr;
};
/* Destructive test of volatile SDRAM 0xd0000000..0xd000ffff only.
 * Requires reviewed TX15 pins, PLL128/AHB64, caches/MPU off, FMC reset/clock off.
 * Caller owns recovery. Never use while the original application is running.
 */
int tx15_sdram_test(volatile struct tx15_sdram_report *r);
#endif
