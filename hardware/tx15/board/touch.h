/* Passive GT911 diagnostic lifecycle; GPL-3.0-or-later. */
#ifndef TX15_TOUCH_H
#define TX15_TOUCH_H
#include "touch_input.h"
enum {TX15_TOUCH_OFF,TX15_TOUCH_PROBING,TX15_TOUCH_READY,TX15_TOUCH_NOT_FOUND,TX15_TOUCH_ERROR};
struct tx15_touch_report {
    uint32_t state,stage,address,frames,errors,busy,bus_status;
    int32_t last_result;
    uint16_t raw_width,raw_height,raw_x,raw_y,x,y;
    uint8_t points,id,map_flags,event;
    char product[5];
};
extern struct tx15_touch_report tx15_touch_report;
void tx15_touch_start(uint32_t now);
void tx15_touch_stop(uint32_t now);
void tx15_touch_poll(uint32_t now);
void tx15_touch_cycle_map(uint32_t now);
int tx15_touch_take(struct tx15_touch_event *event);
#endif
