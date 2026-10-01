/* New Deviation TX15; GPL-3.0-or-later. */
#ifndef TX15_ANALOG_H
#define TX15_ANALOG_H
#include <stdint.h>
/* Physical order: LH, LV, RV, RH, S1, S2. */
extern volatile uint16_t tx15_analog_raw[6];
extern volatile uint32_t tx15_analog_status, tx15_analog_frames;
int tx15_analog_init(void);
int tx15_analog_sample(void);
#endif
