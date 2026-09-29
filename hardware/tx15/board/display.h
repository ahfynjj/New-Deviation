/* New Deviation TX15; GPL-3.0-or-later. */
#ifndef TX15_DISPLAY_H
#define TX15_DISPLAY_H
#include <stdint.h>
#define TX15_LCD_WIDTH 480u
#define TX15_LCD_HEIGHT 320u
#define TX15_LCD_BYTES (TX15_LCD_WIDTH * TX15_LCD_HEIGHT * 2u)
#define TX15_LCD_FB 0xd0000000u
/* Native landscape coordinates mapped to the panel's portrait scan. */
static inline uint32_t tx15_display_offset(unsigned x, unsigned y) {
    return x * TX15_LCD_HEIGHT + (TX15_LCD_HEIGHT - 1u - y);
}
/* Requires PLL128, initialized SDRAM, caches/MPU off and reset LTDC/PLL3.
 * Caller owns reset-context recovery. No persistent writes. */
int tx15_display_init(void);
void tx15_display_pixel(unsigned x, unsigned y, uint16_t color);
void tx15_display_fill(uint16_t color);
#endif
