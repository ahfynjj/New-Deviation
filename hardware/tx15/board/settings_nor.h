#ifndef TX15_SETTINGS_NOR_H
#define TX15_SETTINGS_NOR_H
#include <stdint.h>
/* Region [0xf0000,0x100000) belongs to native settings, never executable. */
#define TX15_SETTINGS_BASE 0xf0000u
extern volatile uint32_t tx15_settings_status;
int tx15_settings_load(unsigned model,void *data,unsigned bytes);
int tx15_settings_save(unsigned model,const void *data,unsigned bytes);
#endif
