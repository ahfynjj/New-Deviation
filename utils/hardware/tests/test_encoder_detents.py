"""TX15 two-edge detents, including bounce and reversal; no board access."""
import unittest
import test_controls as controls

class EncoderDetentTests(unittest.TestCase):
    compile_run = controls.ControlsTests.compile_run

    def test_one_detent_two_edges_and_noise(self):
        self.compile_run(r'''
#include <assert.h>
#include "hardware/tx15/board/inputs.h"
static int next(struct tx15_input_filter *f,unsigned phase){
 return tx15_input_filter_step(f,0,phase).rotation;
}
int main(void){
 struct tx15_input_filter f;
 tx15_input_filter_init(&f,0,3);
 /* Stable detents alternate 3 and 0; two Gray edges per physical click. */
 assert(!next(&f,1));assert(next(&f,0)==1);
 assert(!next(&f,2));assert(next(&f,3)==1);
 assert(!next(&f,2));assert(next(&f,0)==-1);
 assert(!next(&f,1));assert(next(&f,3)==-1);
 /* Returning contact bounce cannot move an item. */
 for(unsigned n=0;n<20;n++){assert(!next(&f,1));assert(!next(&f,3));}
 assert(!next(&f,1));assert(next(&f,0)==1);
 for(unsigned n=0;n<20;n++){assert(!next(&f,1));assert(!next(&f,0));}
 /* Partial reversal cancels, then a real reverse detent emits once. */
 assert(!next(&f,2));assert(!next(&f,0));
 assert(!next(&f,1));assert(next(&f,3)==-1);
 /* Skipped states must clear any partial movement, never guess direction. */
 assert(!next(&f,1));assert(!next(&f,2));assert(!next(&f,3));
 assert(!next(&f,0));assert(!next(&f,1));assert(!next(&f,0));
 /* Holding ENTER blocks rotation without creating release-time backlog. */
 tx15_input_filter_init(&f,TX15_ENTER,3);
 unsigned phase[]={1,0,2,3};
 for(unsigned i=0;i<40;i++)assert(!tx15_input_filter_step(&f,TX15_ENTER,phase[i%4]).rotation);
 assert(!next(&f,1));assert(next(&f,0)==1);
 return 0;
}''', ['hardware/tx15/board/input_filter.c'])
