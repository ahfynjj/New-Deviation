/* New Deviation TX15 MAX board support; GPL-3.0-or-later. */
#ifndef NEW_DEVIATION_TX15_CLOCK_H
#define NEW_DEVIATION_TX15_CLOCK_H
#include <stdint.h>
#define TX15_CORE_HZ 48000000u
enum tx15_clock_result {
    TX15_CLOCK_OK, TX15_CLOCK_BAD_STATE,
    TX15_CLOCK_HSE_TIMEOUT, TX15_CLOCK_SWITCH_TIMEOUT
};
/* Reset HSI64 -> direct crystal HSE48. No PLL, voltage or Flash changes.
 * Keep HSI enabled for recovery. budget bounds register polls, not milliseconds.
 * On failure the caller must stop; a pending switch may still complete later.
 */
enum tx15_clock_result tx15_clock_hse_init(uint32_t budget);
#endif
