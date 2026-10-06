#ifndef TX15_BATTERY_H
#define TX15_BATTERY_H
#include <stdint.h>
extern volatile uint32_t tx15_battery_status,tx15_battery_mv,tx15_battery_raw;
void tx15_battery_init(void);
void tx15_battery_poll(uint32_t now);
#endif
