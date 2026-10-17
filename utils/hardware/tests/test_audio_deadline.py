"""A true 1ms deadline must not expire a transfer at the next millisecond tick."""
import unittest
import test_controls as controls
class AudioDeadlineTests(unittest.TestCase):
    compile_run=controls.ControlsTests.compile_run
    def test_cold_dwt_unlock_enable_without_resetting_shared_counter(self):
        self.compile_run(r'''
#include <assert.h>
#include <stdint.h>
static uint32_t demcr=1,ctrl,locked=1;
static unsigned unlocks;
static uint32_t rd(uint32_t a){
 if(a==0xe000edfc)return demcr;
 if(a==0xe0001000)return ctrl;
 if(a==0xe0001fb4)return locked?3:1;
 if(a==0xe0001004)return 123456;
 return 0;
}
static void wr(uint32_t a,uint32_t v){
 if(a==0xe000edfc){demcr=v;return;}
 if(a==0xe0001fb0){assert(v==0xc5acce55 && (demcr&(1u<<24)));locked=0;unlocks++;return;}
 if(a==0xe0001000){if(!locked)ctrl=v;return;}
 assert(0); /* No cycle counter reset or I2C/pin/clock mutation. */
}
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#include "hardware/tx15/board/controls.c"
int main(void){
 assert(!audio_clock_start());assert(unlocks==1 && ctrl==1 && demcr==0x01000001);
 assert(TX15_AUDIO_CYCLES()==123456);
 assert(!audio_clock_start() && unlocks==1);
 ctrl=1u<<25;assert(audio_clock_start()<0);
 return 0;
}''',['hardware/tx15/board/control_decode.c'])
    def test_tick_boundary_success_and_actual_cycle_timeout_with_wrap(self):
        self.compile_run(r'''
#include <assert.h>
#include <stdint.h>
static uint32_t cycles,tick=100,cr2;
static unsigned phase,index_,count,waits,hang;
static uint32_t regs_[128];
static uint32_t rd(uint32_t a){
 if(a==0x2400e02c)return tick;
 if(a==0x58001c04)return cr2;
 if(a==0x58001c18){
  cycles+=2000;
  if(hang)return 0x8001;
  if(!phase)return 0;
  if(index_<count){if(!waits++){tick++;return 0x8001;}return 2;}
  return 32;
 }
 return regs_[(a>>2)&127];
}
static void wr(uint32_t a,uint32_t v){
 if(a==0x58001c04){cr2=v;if(v&(1u<<14))phase=0;
  else if(v&(1u<<13)){phase=1;count=(v>>16)&255;index_=waits=0;}}
 if(a==0x58001c28){index_++;waits=0;}
 if(a==0x58001c1c)phase=0;
 regs_[(a>>2)&127]=v;
}
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#define TX15_AUDIO_CYCLES() (cycles)
#include "hardware/tx15/board/controls.c"
int main(void){
 tx15_controls_status=1;*(&regs_[(0x58001c00u>>2)&127])=1;
 unsigned start=cycles;assert(!tx15_controls_audio_write(10,0));
 assert(tick>100 && cycles-start<128000); /* Crossed tick, still under true1ms. */
 hang=1;cycles=0xfffff000u;start=cycles;
 assert(tx15_controls_audio_write(10,0)<0);
 assert(cycles-start>=128000 && cycles-start<=132000 && !locked);
 assert(tx15_controls_audio_status()==0x8001);
 return 0;
}''',['hardware/tx15/board/control_decode.c'])
