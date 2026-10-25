"""Pure touch coordinates and cancellation, no hardware or GUI runtime."""
import unittest
import test_controls as controls
class TouchInputTests(unittest.TestCase):
    compile_run=controls.ControlsTests.compile_run
    def test_mapping_corners_rotation_invalid_data_and_event_capture(self):
        self.compile_run(r'''
#include <assert.h>
#include "hardware/tx15/board/touch_input.h"
int main(void){
 struct tx15_touch_map map={320,480,TX15_TOUCH_SWAP};uint16_t x,y;
 assert(!tx15_touch_map_point(&map,0,0,&x,&y) && x==0 && y==0);
 assert(!tx15_touch_map_point(&map,319,479,&x,&y) && x==479 && y==319);
 map.flags|=TX15_TOUCH_FLIP_X|TX15_TOUCH_FLIP_Y;
 assert(!tx15_touch_map_point(&map,0,0,&x,&y) && x==479 && y==319);
 assert(!tx15_touch_map_point(&map,319,479,&x,&y) && x==0 && y==0);
 assert(tx15_touch_map_point(&map,320,0,&x,&y)<0);
 map=(struct tx15_touch_map){480,320,0};
 struct tx15_touch_input in;struct tx15_touch_event event;
 tx15_touch_input_reset(&in);
 tx15_touch_input_frame(&in,&map,1,3,100,100,0xfffffff0u);
 assert(tx15_touch_input_take(&in,&event) && event.kind==TX15_TOUCH_DOWN && event.x==100);
 tx15_touch_input_frame(&in,&map,1,3,101,100,0xfffffff8u);
 assert(!tx15_touch_input_take(&in,&event)); /* one-pixel jitter */
 tx15_touch_input_frame(&in,&map,1,3,102,100,0);
 assert(tx15_touch_input_take(&in,&event) && event.kind==TX15_TOUCH_MOVE && !event.ms);
 tx15_touch_input_frame(&in,&map,0,0,0,0,20);
 assert(tx15_touch_input_take(&in,&event) && event.kind==TX15_TOUCH_UP && event.x==102);
 tx15_touch_input_frame(&in,&map,1,3,100,100,30);
 tx15_touch_input_frame(&in,&map,2,3,100,100,40);
 assert(tx15_touch_input_take(&in,&event) && event.kind==TX15_TOUCH_DOWN);
 assert(tx15_touch_input_take(&in,&event) && event.kind==TX15_TOUCH_CANCEL);
 tx15_touch_input_frame(&in,&map,1,3,105,100,50);assert(!tx15_touch_input_take(&in,&event));
 tx15_touch_input_frame(&in,&map,0,0,0,0,60);
 tx15_touch_input_frame(&in,&map,1,3,100,100,70);
 tx15_touch_input_frame(&in,&map,1,4,100,100,80);
 assert(tx15_touch_input_take(&in,&event) && event.kind==TX15_TOUCH_DOWN);
 assert(tx15_touch_input_take(&in,&event) && event.kind==TX15_TOUCH_CANCEL);
 tx15_touch_input_frame(&in,&map,0,0,0,0,90);
 tx15_touch_input_frame(&in,&map,1,4,480,100,100);
 assert(!tx15_touch_input_take(&in,&event)); /* reject invalid position */
 tx15_touch_input_reset(&in);
 for(unsigned i=0;i<12;i++)tx15_touch_input_frame(&in,&map,1,3,10+i*3,50,i);
 assert(tx15_touch_input_take(&in,&event) && event.kind==TX15_TOUCH_CANCEL);
 assert(!tx15_touch_input_take(&in,&event));
 return 0;
}''',['hardware/tx15/board/touch_input.c'])
