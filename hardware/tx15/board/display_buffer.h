/* Completed-region compositing for native application; GPL-3.0-or-later. */
#ifndef TX15_DISPLAY_BUFFER_H
#define TX15_DISPLAY_BUFFER_H
#include "display.h"
/* Boot staging is dead only AFTER the verified loader jumps to application.
 * Never enable this buffer in the loader, USB updater or RAM bench. */
#define TX15_LCD_SHADOW 0xd0100000u
struct tx15_display_buffer_report {uint32_t state,frames,pixels,last_pixels;};
extern volatile struct tx15_display_buffer_report tx15_display_buffer_report;
void tx15_display_buffer_init(void);
/* Main-thread hardware service only: must not dispatch GUI callbacks. */
void tx15_display_buffer_set_service(void (*service)(void));
void tx15_display_buffer_pixel(unsigned x,unsigned y,uint16_t color);
void tx15_display_buffer_rect(unsigned x,unsigned y,unsigned w,unsigned h,uint16_t color);
void tx15_display_buffer_flush(void);
#endif
