#ifndef TX15_POWER_BUTTON_H
#define TX15_POWER_BUTTON_H
#include <stdint.h>
struct tx15_power_button { uint32_t since; unsigned released,tracking,shutdown; };
/* Arm only after a continuous 20ms release so the boot press cannot shut down.
 * Afterwards require a continuous 2s press. Does not touch hardware/storage. */
int tx15_power_button_poll(struct tx15_power_button *,uint32_t now,int pressed);
#endif
