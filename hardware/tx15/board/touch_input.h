/* Pure single-contact mapping/events; GPL-3.0-or-later. */
#ifndef TX15_TOUCH_INPUT_H
#define TX15_TOUCH_INPUT_H
#include <stdint.h>
enum {TX15_TOUCH_SWAP=1,TX15_TOUCH_FLIP_X=2,TX15_TOUCH_FLIP_Y=4};
enum {TX15_TOUCH_NONE,TX15_TOUCH_DOWN,TX15_TOUCH_MOVE,TX15_TOUCH_UP,TX15_TOUCH_CANCEL};
struct tx15_touch_map {uint16_t width,height;uint8_t flags;};
struct tx15_touch_event {uint32_t ms;uint16_t x,y;uint8_t kind;};
struct tx15_touch_input {
    struct tx15_touch_event queue[8];
    uint16_t x,y;uint8_t active,blocked,id,head,count;
};
int tx15_touch_map_point(const struct tx15_touch_map *,unsigned raw_x,unsigned raw_y,uint16_t *x,uint16_t *y);
void tx15_touch_input_reset(struct tx15_touch_input *);
void tx15_touch_input_cancel(struct tx15_touch_input *,uint32_t now);
void tx15_touch_input_frame(struct tx15_touch_input *,const struct tx15_touch_map *,
                           unsigned count,unsigned id,unsigned raw_x,unsigned raw_y,uint32_t now);
int tx15_touch_input_take(struct tx15_touch_input *,struct tx15_touch_event *);
#endif
