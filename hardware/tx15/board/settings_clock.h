#ifndef TX15_SETTINGS_CLOCK_H
#define TX15_SETTINGS_CLOCK_H
#include <stdint.h>
static inline int tx15_settings_core_clock(uint32_t cr) {
 /* PLL3 may be off or fully ready; it belongs to LCD and is never modified. */
 uint32_t pll3=cr&0x30000000u;
 return (pll3==0 || pll3==0x30000000u) && (cr&0x0f0f001du)==0x03030005u;
}
#endif
