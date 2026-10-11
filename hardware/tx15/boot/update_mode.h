/* Resident update entry and power policy; GPL-3.0-or-later. */
#ifndef TX15_BOOT_UPDATE_MODE_H
#define TX15_BOOT_UPDATE_MODE_H
#include "loader.h"
struct tx15_update_power { uint32_t since; unsigned phase; };
int tx15_boot_update_mode(unsigned exit_stable,enum tx15_boot_load_result);
int tx15_update_power_poll(struct tx15_update_power*,uint32_t now,unsigned pressed,unsigned busy);
unsigned tx15_boot_exit_stable(void);
void tx15_boot_update_run(uint32_t jedec) __attribute__((noreturn));
#endif
