#ifndef DEVIATION_EMU_TOUCH_H
#define DEVIATION_EMU_TOUCH_H

/* Window coordinates to logical LCD coordinates. Outside clicks are not touches. */
static inline int EMU_MapTouch(int window_x, int window_y, int top,
                              unsigned screen_w, unsigned screen_h,
                              unsigned lcd_w, unsigned lcd_h,
                              unsigned *x, unsigned *y)
{
    int local_y = window_y - top;
    if (!screen_w || !screen_h || !lcd_w || !lcd_h || window_x < 0 || local_y < 0
        || (unsigned)window_x >= screen_w || (unsigned)local_y >= screen_h)
        return 0;
    *x = (unsigned)window_x * lcd_w / screen_w;
    *y = (unsigned)local_y * lcd_h / screen_h;
    return 1;
}

#endif
