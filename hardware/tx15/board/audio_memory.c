#include "audio_memory.h"
#ifndef TX15_READ32
#define TX15_READ32(a) (*(volatile uint32_t *)(a))
#define TX15_WRITE32(a,v) (*(volatile uint32_t *)(a)=(v))
#endif
#ifndef TX15_AUDIO_BARRIER
#define TX15_AUDIO_BARRIER() __asm volatile("dsb" ::: "memory")
#endif
int tx15_audio_memory_init(void) {
    static unsigned initialized;
    if(initialized)return 0;
    /* Native loader contract currently leaves caches and MPU disabled. */
    if((TX15_READ32(0xe000ed14u)&0x30000u) || (TX15_READ32(0xe000ed94u)&1u))return -1;
    TX15_WRITE32(0x580244dcu,TX15_READ32(0x580244dcu)|0x60000000u);
    if((TX15_READ32(0x580244dcu)&0x60000000u)!=0x60000000u)return -1;
    for(uint32_t a=TX15_AUDIO_D2_BASE;a<TX15_AUDIO_D2_BASE+TX15_AUDIO_D2_BYTES;a+=4)
        TX15_WRITE32(a,0);
    TX15_AUDIO_BARRIER();initialized=1;return 0;
}
