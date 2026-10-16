/* Application-owned D2 workspace. No new ELF load segment; GPL-3.0-or-later. */
#ifndef TX15_AUDIO_MEMORY_H
#define TX15_AUDIO_MEMORY_H
#include <stdint.h>
#define TX15_AUDIO_D2_BASE 0x30000000u
#define TX15_AUDIO_LUA_BYTES (160u*1024u)
#define TX15_AUDIO_PCM_BASE (TX15_AUDIO_D2_BASE+TX15_AUDIO_LUA_BYTES)
#define TX15_AUDIO_DMA_BASE (TX15_AUDIO_PCM_BASE+16u*1024u)
#define TX15_AUDIO_D2_BYTES (192u*1024u)
#define TX15_AUDIO_HALF_FRAMES 512u
#define TX15_AUDIO_HALF_WORDS TX15_AUDIO_HALF_FRAMES
int tx15_audio_memory_init(void);
#endif
