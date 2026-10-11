/* Minimal resident update screen; GPL-3.0-or-later. */
#ifndef TX15_UPDATE_SCREEN_H
#define TX15_UPDATE_SCREEN_H
#include "receiver.h"
void tx15_update_screen(const struct tx15_update_reply*,unsigned connected,unsigned writable);
/* 0=power latched, 1=loading, 2=starting. Pure framebuffer operations. */
void tx15_boot_screen(unsigned stage,uint32_t completed,uint32_t total);
#endif
