"""GT911 passive discovery and incremental frame transactions."""
import unittest
import test_controls as controls
class TouchDriverTests(unittest.TestCase):
    compile_run=controls.ControlsTests.compile_run
    def test_identity_frame_ack_errors_busy_and_explicit_stop(self):
        self.compile_run(r'''
#include <assert.h>
#include "hardware/tx15/board/touch.h"
#include "hardware/tx15/board/i2c_bus.h"
volatile struct tx15_i2c_report tx15_i2c_report;
static unsigned calls,writes,ready,bad_id,io,busy;
static uint8_t point[8]={3,0x3f,1,0xdf,1,10,0,0};
int tx15_i2c_read(unsigned address,unsigned reg,unsigned prefix,uint8_t *data,unsigned n){
 calls++;assert(prefix==2 && n && n<=4);
 if(busy)return TX15_I2C_BUSY;
 if(io || address!=0x14){tx15_i2c_report.status=16;return TX15_I2C_IO;}
 tx15_i2c_report.status=32;
 if(reg==0x8140){assert(n==4);data[0]=bad_id?'X':'9';data[1]='1';data[2]='1';data[3]=0;}
 else if(reg==0x8048){assert(n==4);data[0]=0x40;data[1]=1;data[2]=0xe0;data[3]=1;}
 else if(reg==0x814e){assert(n==1);data[0]=ready;}
 else {assert((reg==0x814f || reg==0x8153) && n==4);
  for(unsigned i=0;i<n;i++)data[i]=point[reg-0x814f+i];}
 return 0;
}
int tx15_i2c_write(unsigned address,unsigned reg,unsigned prefix,const uint8_t *data,unsigned n){
 calls++;assert(!io && address==0x14 && reg==0x814e && prefix==2 && n==1 && !*data);
 writes++;ready=0;return 0;
}
static void advance(unsigned start,unsigned end){
 for(unsigned ms=start;ms<end;ms++){
  tx15_touch_poll(ms);unsigned before=calls;tx15_touch_poll(ms);assert(calls==before);
 }
}
int main(void){
 struct tx15_touch_event event;
 tx15_touch_start(0);advance(0,10);
 assert(tx15_touch_report.state==TX15_TOUCH_READY && tx15_touch_report.address==0x14);
 assert(tx15_touch_report.raw_width==320 && tx15_touch_report.raw_height==480);
 assert(tx15_touch_report.map_flags==TX15_TOUCH_SWAP && !writes);
 ready=0x81;advance(10,40);
 assert(writes==1 && tx15_touch_report.frames==1);
 assert(tx15_touch_report.raw_x==319 && tx15_touch_report.raw_y==479);
 assert(tx15_touch_take(&event) && event.kind==TX15_TOUCH_DOWN && event.x==479 && event.y==319);
 assert(!tx15_touch_take(&event));
 advance(40,80);assert(!tx15_touch_take(&event)); /* not-ready is not release */
 ready=0x80;advance(80,110);
 assert(tx15_touch_take(&event) && event.kind==TX15_TOUCH_UP);
 ready=0x81;advance(110,140);
 assert(tx15_touch_take(&event) && event.kind==TX15_TOUCH_DOWN);
 io=1;advance(140,160);
 assert(tx15_touch_report.state==TX15_TOUCH_ERROR && tx15_touch_report.bus_status==16);
 assert(tx15_touch_take(&event) && event.kind==TX15_TOUCH_CANCEL);
 unsigned before=calls;advance(160,200);assert(calls==before);
 io=0;bad_id=1;before=writes;tx15_touch_start(200);advance(200,220);
 assert(tx15_touch_report.state==TX15_TOUCH_NOT_FOUND && writes==before);
 bad_id=0;busy=1;tx15_touch_start(0xfffffff0u);
 advance(0,600);assert(tx15_touch_report.state==TX15_TOUCH_ERROR);
 busy=0;tx15_touch_start(600);advance(600,620);
 tx15_touch_stop(620);before=calls;advance(620,1000);
 assert(calls==before && tx15_touch_report.state==TX15_TOUCH_OFF);
 return 0;
}''',['hardware/tx15/board/touch.c','hardware/tx15/board/touch_input.c'])
