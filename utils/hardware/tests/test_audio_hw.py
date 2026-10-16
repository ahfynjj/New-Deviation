"""Native codec startup and DMA transport: bounded, silent on failure."""
import unittest
import test_controls as controls

class AudioHardwareTests(unittest.TestCase):
    compile_run=controls.ControlsTests.compile_run
    def test_transport_clock_dma_order_and_silent_underrun(self):
        self.compile_run(r'''
#include <assert.h>
#include <stdint.h>
#include "hardware/tx15/board/audio.h"
#include "hardware/tx15/board/audio_memory.h"
volatile struct tx15_audio_report tx15_audio_report;
static uint32_t address[256],value[256],used,pcm[TX15_AUDIO_D2_BYTES/4];
static uint32_t *reg(uint32_t a){for(unsigned i=0;i<used;i++)if(address[i]==a)return &value[i];assert(used<256);address[used]=a;return &value[used++];}
static uint32_t rd(uint32_t a){return *reg(a);}
static void wr(uint32_t a,uint32_t v){
 assert(a!=0x58024440 && a!=0x58024444 && a!=0x58024458); /* No PLL3/I2C kernel edits. */
 assert(a<0x58001c00 || a>0x58001c28); /* No I2C in transport or IRQ. */
 if(a==0x58024400){assert((v&~0x0c000000u)==(rd(a)&~0x0c000000u));if(v&(1u<<26))v|=1u<<27;else v&=~(1u<<27);}
 if(a==0x4002000c)*reg(0x40020004)&=~v;
 *reg(a)=v;
}
static uint32_t *word(uint32_t a){assert(a>=TX15_AUDIO_PCM_BASE && a<TX15_AUDIO_D2_BASE+TX15_AUDIO_D2_BYTES && !(a&3));return &pcm[(a-TX15_AUDIO_D2_BASE)/4];}
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#define TX15_AUDIO_WORD(a) (*word(a))
#define TX15_AUDIO_BARRIER() ((void)0)
#include "hardware/tx15/board/audio_transport.c"
int main(void){
 *reg(0x58024400)=0x33030005; /* PLL1 and LCD PLL3 in use. */
 *reg(0x58024428)=0x00c000c2;
 *reg(0x5802442c)=0x01010808;
 assert(!tx15_audio_transport_init());assert(tx15_audio_transport_ready()==1);
 assert((rd(0x58024428)&0x3f00000)==0xc00000); /* LCD M3 unchanged. */
 assert((rd(0x58024428)>>12&63)==12);
 assert((rd(0x58024438)&511)==97 && (rd(0x58024438)>>9&127)==7);
 assert(rd(0x5802443c)==(2490u<<3));
 assert(rd(0x40003850)==0x02030005); /* Master TX,16-bit,I2S,MCLK,divide 6. */
 tx15_audio_transport_start();
 assert(rd(0x40020074)==1024 && rd(0x40020078)==0x40003820);
 assert(rd(0x4002007c)==TX15_AUDIO_DMA_BASE);
 assert(rd(0x40020080)==TX15_AUDIO_DMA_BASE+2048);
 assert(rd(0x40020810)==40 && (rd(0x40003800)&0x201)==0x201);
 tx15_audio_transport_tone(9600);tx15_audio_transport_poll(10);
 *reg(0x40020070)|=1u<<19;*reg(0x40020004)=32;
 DMA1_Stream4_IRQHandler();assert(tx15_audio_report.dma_irqs==1);
 unsigned nonzero=0;for(unsigned i=0;i<512;i++)nonzero+=*word(TX15_AUDIO_DMA_BASE+4*i)!=0;
 assert(nonzero>400);
 /* No producer refill: next use of this half must become silence. */
 *reg(0x40020004)=32;DMA1_Stream4_IRQHandler();
 for(unsigned i=0;i<512;i++)assert(!*word(TX15_AUDIO_DMA_BASE+4*i));
 assert(tx15_audio_report.underruns==1);
 *reg(0x40020004)=8;DMA1_Stream4_IRQHandler();
 assert(tx15_audio_report.errors && tx15_audio_transport_ready()<0);
 tx15_audio_transport_stop();assert(!(rd(0x40020070)&1));
 assert((rd(0x58024400)&0x3f000000)==0x33000000);
 return 0;
}''',[])
    def test_shared_bus_audio_nack_is_bounded_and_controls_still_sample(self):
        self.compile_run(r'''
#include <assert.h>
#include <stdint.h>
static unsigned tick,phase,index_,addr,count,read_mode,nack,writes,bus_resets,audio_mode;
static uint32_t regs_[128],cr2;
static uint32_t rd(uint32_t a){
 if(a==0x2400e02c)return tick;
 if(a==0x58024400)return 5;
 if(a==0x58001c04)return cr2;
 if(a==0x58001c18){
  if(nack)tick++;
  if(nack && addr==0x18 && phase)return 16;
  if(!phase)return 0;
  if(index_<count)return read_mode?4:2;
  return (cr2&(1u<<25))?32:64;
 }
 if(a==0x58001c24){index_++;return addr==0x18?0:255;}
 return regs_[(a>>2)&127];
}
static void wr(uint32_t a,uint32_t v){
 if(a==0x5802449c && (v&128))bus_resets++;
 if(a==0x58001c04){
  cr2=v;if(v&(1u<<14))phase=0;
  else if(v&(1u<<13)){addr=(v>>1)&127;count=(v>>16)&255;read_mode=(v>>10)&1;phase=1;index_=0;}
 }
 if(a==0x58001c28){index_++;writes++;}
 if(a==0x58001c1c)phase=0;
 if(audio_mode)assert(a>=0x58001c00 && a<=0x58001c28); /* No bus/GPIO reset. */
 regs_[(a>>2)&127]=v;
}
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#include "hardware/tx15/board/controls.c"
int main(void){
 /* Fake ticks advance at each status read: widen normal setup clock only. */
 tick=0;assert(!bus_init());tx15_controls_status=1;
 unsigned resets=bus_resets;audio_mode=1;nack=1;
 unsigned before=tick;assert(tx15_controls_audio_write(0,1)<0);assert(tick-before<10);
 assert(tx15_controls_status==1 && bus_resets==resets);
 audio_mode=0;nack=0;tick=100;
 assert(!locked);
 assert(!tx15_controls_audio_write(0,1));
 uint8_t page;assert(!tx15_controls_audio_read(0,&page) && page==0);
 tx15_controls_poll(100);assert(tx15_controls_status==1 && tx15_controls_frames==1);
 assert(bus_resets==resets);
 locked=1;unsigned before_writes=writes;
 assert(tx15_controls_audio_write(0,1)<0 && writes==before_writes);locked=0;
 return 0;
}''',['hardware/tx15/board/control_decode.c'])
    def test_codec_steps_are_cooperative_muted_until_ready_and_abort_on_nack(self):
        self.compile_run(r'''
#include <assert.h>
#include <stdint.h>
#include "hardware/tx15/board/audio.h"
static unsigned writes,failed,resets,clock_ready,started,stopped,memory_ready;
static unsigned now,page,regs[2][128],current_reset;
int tx15_audio_memory_init(void){memory_ready=1;return 0;}
int tx15_audio_transport_init(void){assert(memory_ready);return 0;}
int tx15_audio_transport_ready(void){return clock_ready;}
void tx15_audio_transport_start(void){started++;}
void tx15_audio_transport_stop(void){stopped++;}
void tx15_audio_transport_poll(unsigned t){(void)t;}
int tx15_audio_transport_tone(unsigned frames){assert(frames==9600);if(!tx15_audio_report.volume)assert(regs[1][48]==0);return 1;}
void tx15_audio_reset_pin(unsigned high){current_reset=high;resets++;}
int tx15_controls_audio_write(unsigned reg,unsigned value){
 writes++;if(failed)return -1;assert(current_reset);
 assert(reg<128 && value<256);
 if(reg==0)page=value;else {assert(page<2);regs[page][reg]=value;}
 return 0;
}
int tx15_controls_audio_read(unsigned reg,uint8_t *value){(void)reg;if(failed)return -1;*value=0;return 0;}
#include "hardware/tx15/board/audio.c"
int main(void){
 assert(!tx15_audio_hw_init());assert(!writes && !started); /* Default off. */
 tx15_audio_hw_poll(0);assert(!writes);
 assert(tx15_audio_hw_test(0));
 for(now=0;now<100;now++) {
  unsigned previous=writes;tx15_audio_hw_poll(now);assert(writes-previous<=1);
  assert(!started);
 }
 clock_ready=1;
 for(;now<300;now++) {unsigned previous=writes;tx15_audio_hw_poll(now);assert(writes-previous<=1);}
 assert(tx15_audio_report.state==TX15_AUDIO_READY && started==1);
 assert(regs[0][4]==0 && regs[0][11]==0x82 && regs[0][12]==0x81);
 assert(regs[0][13]==0 && regs[0][14]==128 && regs[0][27]==0);
 assert(regs[1][48]==0x10 && regs[1][45]==2);
 tx15_audio_hw_volume(20);tx15_audio_hw_poll(now++);
 assert(tx15_audio_report.volume==5); /* A0 caps the diagnostic at low gain. */
 tx15_audio_hw_stop();assert(!current_reset && stopped && tx15_audio_report.state==TX15_AUDIO_OFF);
 tx15_audio_hw_volume(0);assert(tx15_audio_hw_test(now));
 unsigned end=now+300;for(;now<end;now++)tx15_audio_hw_poll(now);
 assert(tx15_audio_report.state==TX15_AUDIO_READY && regs[1][48]==0);
 tx15_audio_hw_stop();
 failed=1;assert(tx15_audio_hw_test(now));
 for(unsigned i=0;i<20;i++)tx15_audio_hw_poll(now++);
 assert(tx15_audio_report.state==TX15_AUDIO_ERROR && !current_reset);
 assert(tx15_audio_report.errors && resets);
 failed=0;clock_ready=0;assert(tx15_audio_hw_test(now));
 tx15_audio_hw_poll(now+501);
 assert(tx15_audio_report.state==TX15_AUDIO_ERROR && !current_reset);
 return 0;
}''',[])
