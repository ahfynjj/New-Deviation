"""Touch sampling uses actual native runtime without GUI dispatch."""
import unittest
import test_switch_upgrade as switches
class TouchRuntimeTests(unittest.TestCase):
    run_c=switches.SwitchUpgradeTests.run_c
    def test_sampling_runs_between_medium_ticks_and_controls_go_first(self):
        self.run_c(r'''
#include <assert.h>
#define TX15_TOUCH_DIAGNOSTIC 1
#include "common.h"
#include "hardware/tx15/board/touch.h"
volatile u8 priority_ready;
static unsigned sampled_count,touch_count,last_controls;
void tx15_controls_poll(unsigned now){last_controls=now;}
int tx15_analog_sample(void){sampled_count++;return 0;}
void tx15_touch_poll(uint32_t now){
 touch_count++;if(now && now%5==0)assert(last_controls==now);
}
#include "src/target/tx/radiomaster/tx15/runtime.c"
int main(void){
 for(unsigned now=0;now<=20;now++)tx15_runtime_poll(now);
 assert(sampled_count==4 && touch_count==21);return 0;
}''',[])
