/* New Deviation TX15; GPL-3.0-or-later. */
#ifndef TX15_DISPLAY_H
#define TX15_DISPLAY_H
#include <stdint.h>
#define TX15_LCD_WIDTH 480u
#define TX15_LCD_HEIGHT 320u
#define TX15_LCD_BYTES (TX15_LCD_WIDTH * TX15_LCD_HEIGHT * 2u)
#define TX15_LCD_FB 0xd0000000u
/* ST7365 MADCTL=0xe8 already selects landscape address order. The LTDC
 * 320x480 scan timing does not require a second software rotation. */
static inline uint32_t tx15_display_offset(unsigned x, unsigned y) {
    return y * TX15_LCD_WIDTH + x;
}
/* Requires PLL128, initialized SDRAM, caches/MPU off and reset LTDC/PLL3.
 * Caller owns reset-context recovery. No persistent writes. */
int tx15_display_init(void);
void tx15_display_pixel(unsigned x, unsigned y, uint16_t color);
void tx15_display_fill(uint16_t color);
#endif
