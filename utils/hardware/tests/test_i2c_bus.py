"""Shared I2C4 protocol, admission, deadline and terminal-status regression."""
import unittest
import test_controls as controls

class SharedI2CTests(unittest.TestCase):
    compile_run=controls.ControlsTests.compile_run
    def test_register_width_payload_lock_and_timeout(self):
        self.compile_run(r'''
#include <assert.h>
#include <stdint.h>
#include "hardware/tx15/board/i2c_bus.h"
static uint32_t regs_[128],cr2,cycles;
static unsigned phase,index_,bytes,reading,nack,stall,frozen,inject,all_writes,per_read=1000;
static uint8_t sent[16];static unsigned sent_count;
static uint32_t rd(uint32_t a){
 if(a==0x58001c04)return cr2;
 if(a==0x58001c18){
  if(!frozen)cycles+=per_read;
  if(nack && phase)return 16;
  if(stall)return 0x8000;
  if(!phase)return 0;
  if(index_<bytes)return reading?4:2;
  return cr2&(1u<<25)?32:64;
 }
 if(a==0x58001c24){index_++;return 0xa0+index_;}
 return regs_[(a>>2)&127];
}
static void wr(uint32_t a,uint32_t v){
 assert(a>=0x58001c00 && a<=0x58001c28);all_writes++;
 if(a==0x58001c04){cr2=v;if(v&(1u<<14))phase=0;
  else if(v&(1u<<13)){phase=1;index_=0;bytes=(v>>16)&255;reading=(v>>10)&1;}}
 if(a==0x58001c28){
  assert(sent_count<16);sent[sent_count++]=v;index_++;
  if(inject){inject=0;unsigned before=all_writes;uint8_t value;
   assert(tx15_i2c_read(0x5d,0x814e,2,&value,1)==TX15_I2C_BUSY);
   assert(before==all_writes);}
 }
 if(a==0x58001c1c)phase=0;
 regs_[(a>>2)&127]=v;
}
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#define TX15_AUDIO_CYCLES() (cycles)
#include "hardware/tx15/board/controls.c"
int main(void){
 tx15_controls_status=1;regs_[(0x58001c00u>>2)&127]=1;
 uint8_t data[4]={0};inject=1;
 assert(tx15_i2c_read(0x5d,0x8140,2,data,4)==TX15_I2C_OK);
 assert(sent_count==2 && sent[0]==0x81 && sent[1]==0x40);
 assert(data[0]==0xa1 && data[3]==0xa4 && !locked);
 sent_count=0;uint8_t zero=0;
 assert(!tx15_i2c_write(0x5d,0x814e,2,&zero,1));
 assert(sent_count==3 && sent[0]==0x81 && sent[1]==0x4e && sent[2]==0);
 unsigned before=all_writes;
 assert(tx15_i2c_read(0x5d,0x8140,2,data,5)==TX15_I2C_INVALID);
 assert(tx15_i2c_read(0x5d,0x8140,1,data,1)==TX15_I2C_INVALID);
 assert(tx15_i2c_read(0x5d,0,0,data,1)==TX15_I2C_INVALID);
 assert(tx15_i2c_read(0x78,0,1,data,1)==TX15_I2C_INVALID);
 assert(all_writes==before);
 sent_count=0;per_read=20000;cycles=0;
 assert(tx15_i2c_read(0x5d,0x8140,2,data,4)==TX15_I2C_IO);
 assert(cycles>=128000 && !locked); /* individually ready stages exceed total deadline */
 per_read=1000;
 nack=1;sent_count=0;assert(tx15_i2c_read(0x5d,0x8140,2,data,4)==TX15_I2C_IO);
 assert(tx15_i2c_report.status==16 && tx15_i2c_report.errors==2 && !locked);
 assert(tx15_controls_status==1 && regs_[(0x58001c00u>>2)&127]==1);
 nack=0;stall=1;cycles=0xfffff000u;unsigned start=cycles;
 assert(tx15_i2c_read(0x14,0x8140,2,data,4)==TX15_I2C_IO);
 assert(cycles-start>=128000 && cycles-start<=132000 && !locked);
 frozen=1;assert(tx15_i2c_read(0x14,0x8140,2,data,4)==TX15_I2C_IO);
 tx15_controls_status=2;before=all_writes;
 assert(tx15_i2c_read(0x5d,0x8140,2,data,4)==TX15_I2C_UNAVAILABLE);
 assert(all_writes==before);return 0;
}''',['hardware/tx15/board/control_decode.c'])
