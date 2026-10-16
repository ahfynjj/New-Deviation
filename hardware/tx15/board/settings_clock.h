#ifndef TX15_SETTINGS_CLOCK_H
#define TX15_SETTINGS_CLOCK_H
#include <stdint.h>
static inline int tx15_settings_core_clock(uint32_t cr) {
 /* PLL2 (audio) / PLL3 (LCD) may be off or fully ready; never modified here. */
 uint32_t pll2=cr&0x0c000000u;
 uint32_t pll3=cr&0x30000000u;
 return (pll2==0 || pll2==0x0c000000u) && (pll3==0 || pll3==0x30000000u)
     && (cr&0x030f001du)==0x03030005u;
}
#endif
