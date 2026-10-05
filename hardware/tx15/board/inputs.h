/* New Deviation TX15; GPL-3.0-or-later. */
#ifndef TX15_INPUTS_H
#define TX15_INPUTS_H
#include <stdint.h>
enum { TX15_ENTER=1, TX15_EXIT=2, TX15_PREV=4, TX15_NEXT=8 };
struct tx15_input_event { unsigned pressed; int rotation; };
struct tx15_input_filter {
    unsigned stable, candidate, age[12], phase;
    int partial;
};
void tx15_input_filter_init(struct tx15_input_filter *f,unsigned keys,unsigned phase);
struct tx15_input_event tx15_input_filter_step(struct tx15_input_filter *f,unsigned keys,unsigned phase);
unsigned tx15_inputs_state(void);
void tx15_inputs_init(void);
void tx15_inputs_tick(void); /* Called once per millisecond, no drawing. */
struct tx15_input_event tx15_inputs_take(void); /* Main loop, IRQ-safe. */
#endif
