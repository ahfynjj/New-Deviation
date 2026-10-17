"""PLL outputs are write-protected while running; media clock is permanent."""
import unittest
import test_controls as controls
class MediaClockTests(unittest.TestCase):
    compile_run=controls.ControlsTests.compile_run
    def test_fixed_pll2_outputs_enabled_before_start_and_reuse_never_reprograms(self):
        self.compile_run(r'''
#include <assert.h>
#include <stdint.h>
#include "hardware/tx15/board/media_clock.h"
static uint32_t a_[80],v_[80],used,writes;
static uint32_t *reg(uint32_t a){for(unsigned i=0;i<used;i++)if(a_[i]==a)return &v_[i];assert(used<80);a_[used]=a;return &v_[used++];}
static uint32_t rd(uint32_t a){return *reg(a);}
static void wr(uint32_t a,uint32_t v){
 assert(a!=0x58024430 && a!=0x58024440 && a!=0x58024444);
 if(a==0x5802442c){assert(!((v^rd(a))&~0x3800f0u));assert(!(rd(0x58024400)&0x0c000000));}
 if(a==0x58024428){assert(!((v^rd(a))&~0x3f000u));assert(!(rd(0x58024400)&0x0c000000));}
 if(a==0x58024438 || a==0x5802443c)assert(!(rd(0x58024400)&0x0c000000));
 if(a==0x58024400){assert((v&~0x0c000000u)==(rd(a)&~0x0c000000u));assert(rd(0x5802442c)&(1u<<21));v|=1u<<27;}
 *reg(a)=v;writes++;
}
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#include "hardware/tx15/board/media_clock.c"
int main(void){
 *reg(0x58024400)=0x33030005;*reg(0x58024410)=0x1b;*reg(0x58024418)=0x48;
 *reg(0x58024428)=0x00c000c2;*reg(0x5802442c)=0x01010808;*reg(0x58024430)=0x0101023f;
 /* A PLL2 owned by someone else is never stopped or reconfigured. */
 *reg(0x58024400)|=0x0c000000;assert(tx15_media_clock_init()<0 && !writes);
 *reg(0x58024400)&=~0x0c000000u;
 assert(!tx15_media_clock_init() && tx15_media_clock_ready()==1);
 assert((rd(0x5802442c)&0x3800f0)==0x280090);
 assert(!(rd(0x5802442c)&(1u<<17))); /* CPU PLL1Q remains off. */
 assert(rd(0x58024438)==0x01010e61 && rd(0x5802443c)==2490u<<3);
 unsigned before=writes;assert(!tx15_media_clock_init() && writes==before);
 *reg(0x5802442c)&=~(1u<<21);assert(tx15_media_clock_ready()<0 && writes==before);
 return 0;
}''',[])
