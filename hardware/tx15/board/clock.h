/* New Deviation TX15 MAX board support; GPL-3.0-or-later. */
#ifndef NEW_DEVIATION_TX15_CLOCK_H
#define NEW_DEVIATION_TX15_CLOCK_H
#include <stdint.h>
#define TX15_CORE_HZ 48000000u
#define TX15_PLL_CORE_HZ 128000000u
enum tx15_clock_result {
    TX15_CLOCK_OK, TX15_CLOCK_BAD_STATE,
    TX15_CLOCK_HSE_TIMEOUT, TX15_CLOCK_SWITCH_TIMEOUT, TX15_CLOCK_PLL_TIMEOUT
};
/* Reset HSI64 -> direct crystal HSE48. No PLL, voltage or Flash changes.
 * Keep HSI enabled for recovery. budget bounds register polls, not milliseconds.
 * On failure the caller must stop; a pending switch may still complete later.
 */
enum tx15_clock_result tx15_clock_hse_init(uint32_t budget);
/* From confirmed HSE48: PLL1 P=128 MHz, AHB=64 MHz, APB1..4=32 MHz.
 * Requires valid internal LDO voltage and existing Flash latency >=1.
 * Does not alter PWR/Flash. Caller must stop and recover on any error.
 */
enum tx15_clock_result tx15_clock_pll128_init(uint32_t budget);
#endif
