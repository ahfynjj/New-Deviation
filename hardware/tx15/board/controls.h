/* TX15 factory switches and trims; GPL-3.0-or-later. */
#ifndef TX15_CONTROLS_H
#define TX15_CONTROLS_H
#include <stdint.h>
struct tx15_controls {
    uint8_t position[7], candidate[6];
    uint32_t since[6], buttons_since;
    unsigned valid, trims, buttons, buttons_candidate;
};
void tx15_controls_reset(struct tx15_controls *c);
void tx15_controls_invalidate(struct tx15_controls *c);
void tx15_controls_decode(struct tx15_controls *c, uint16_t port74, uint16_t port75, unsigned now);
/* 1=active, 0=inactive, -1=unavailable/invalid. */
int tx15_controls_switch(const struct tx15_controls *c, unsigned group, unsigned position);
extern struct tx15_controls tx15_controls;
extern volatile uint32_t tx15_controls_status, tx15_controls_frames, tx15_controls_errors;
extern volatile uint16_t tx15_controls_raw[2];
int tx15_controls_init(void);
void tx15_controls_poll(unsigned now);
#endif
