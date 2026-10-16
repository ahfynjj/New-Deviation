"""D2 workspace initialization and ownership, independent of loader segments."""
import unittest
import test_controls as controls

class AudioMemoryTests(unittest.TestCase):
    compile_run=controls.ControlsTests.compile_run
    def test_clock_before_clear_alignment_bounds_and_cache_rejection(self):
        self.compile_run(r'''
#include <assert.h>
#include <stdint.h>
#include "hardware/tx15/board/audio_memory.h"
static uint32_t words[TX15_AUDIO_D2_BYTES/4],clock_bits,ccr,mpu,clears;
static uint32_t rd(uint32_t a){
 if(a==0x580244dc)return clock_bits;
 if(a==0xe000ed14)return ccr;
 if(a==0xe000ed94)return mpu;
 assert(0);return 0;
}
static void wr(uint32_t a,uint32_t v){
 if(a==0x580244dc){clock_bits=v;return;}
 assert((clock_bits&0x60000000)==0x60000000);
 assert(a>=TX15_AUDIO_D2_BASE && a<TX15_AUDIO_D2_BASE+TX15_AUDIO_D2_BYTES && !(a&3));
 words[(a-TX15_AUDIO_D2_BASE)/4]=v;clears++;
}
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#define TX15_AUDIO_BARRIER() ((void)0)
#include "hardware/tx15/board/audio_memory.c"
int main(void){
 assert(TX15_AUDIO_LUA_BYTES==160*1024);
 assert(TX15_AUDIO_PCM_BASE==TX15_AUDIO_D2_BASE+TX15_AUDIO_LUA_BYTES);
 assert(TX15_AUDIO_DMA_BASE>=TX15_AUDIO_PCM_BASE+16384);
 assert(!(TX15_AUDIO_DMA_BASE&31) && !(TX15_AUDIO_D2_BYTES&31));
 assert(TX15_AUDIO_D2_BYTES<=256*1024);
 ccr=1u<<16;assert(tx15_audio_memory_init()<0 && !clears);
 ccr=0;mpu=1;assert(tx15_audio_memory_init()<0 && !clears);
 mpu=0;assert(!tx15_audio_memory_init());assert(clears==TX15_AUDIO_D2_BYTES/4);
 unsigned previous=clears;assert(!tx15_audio_memory_init() && clears==previous);
 return 0;
}''',[])
