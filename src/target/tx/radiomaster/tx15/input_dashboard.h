/* Native read-only physical control dashboard; GPL-3.0-or-later. */
#ifndef TX15_INPUT_DASHBOARD_H
#define TX15_INPUT_DASHBOARD_H
#include "buttons.h"
#define TX15_DASHBOARD_BUILD "MON1"
#define TX15_DASHBOARD_TILES 15
struct tx15_dashboard_state {
    s16 percent[6],trim[4];
    s8 position[6],selected;
    u8 analog_valid,trim_bound,trim_pressed,buttons;
    u16 raw[2];
};
void tx15_dashboard_collect(struct tx15_dashboard_state *state);
void tx15_dashboard_draw(unsigned tile,const struct tx15_dashboard_state *state);
void tx15_input_dashboard_init(buttonAction_t *action);
void tx15_input_dashboard_event(void);
#endif
