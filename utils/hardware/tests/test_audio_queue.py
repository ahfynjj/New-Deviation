"""Bounded audio requests: priority, FIFO, event coalescing and alarm room."""
import unittest
import test_controls as controls
class AudioQueueTests(unittest.TestCase):
    compile_run=controls.ControlsTests.compile_run
    def test_priorities_fifo_event_merge_and_reserved_alarm_capacity(self):
        self.compile_run(r'''
#include <assert.h>
#include <string.h>
#include "src/audio/queue.h"
int main(void){
 struct nd_audio_queue q;struct nd_audio_request out;
 nd_audio_queue_init(&q);assert(sizeof(q)<2400);
 for(unsigned i=0;i<14;i++)assert(nd_audio_queue_push(&q,"/SOUNDS/cn/test.wav",ND_AUDIO_NORMAL,i+1));
 assert(!nd_audio_queue_push(&q,"low.wav",ND_AUDIO_LUA,90));
 assert(nd_audio_queue_push(&q,"alarm.wav",ND_AUDIO_ALERT,90));
 assert(nd_audio_queue_push(&q,"timer.wav",ND_AUDIO_ALERT,91));
 assert(q.count==16 && q.peak==16);
 assert(!nd_audio_queue_push(&q,"low.wav",ND_AUDIO_NORMAL,92));
 /* A new alarm evicts oldest lowest-priority item, never another alarm. */
 assert(nd_audio_queue_push(&q,"critical.wav",ND_AUDIO_ALERT,92));
 assert(q.evicted==1 && q.count==16);
 assert(nd_audio_queue_pop(&q,&out) && out.event_id==90);
 assert(nd_audio_queue_pop(&q,&out) && out.event_id==91);
 assert(nd_audio_queue_pop(&q,&out) && out.event_id==92);
 assert(nd_audio_queue_pop(&q,&out) && out.event_id==2);
 assert(nd_audio_queue_push(&q,"latest.wav",ND_AUDIO_TIMER,3));
 assert(q.merged==1);
 assert(nd_audio_queue_pop(&q,&out) && out.event_id==3 && !strcmp(out.path,"latest.wav"));
 /* Matching event coalesces even when nominal normal capacity was full. */
 nd_audio_queue_clear(&q);
 assert(nd_audio_queue_push(&q,"high.wav",ND_AUDIO_ALERT,1));
 assert(nd_audio_queue_push(&q,"updated.wav",ND_AUDIO_NORMAL,1));
 assert(q.count==1);assert(nd_audio_queue_pop(&q,&out) && out.priority==ND_AUDIO_ALERT);
 assert(!strcmp(out.path,"updated.wav"));
 return 0;
}''',['src/audio/queue.c'])

    def test_empty_long_paths_and_full_equal_priority_do_not_corrupt_queue(self):
        self.compile_run(r'''
#include <assert.h>
#include <string.h>
#include "src/audio/queue.h"
int main(void){
 struct nd_audio_queue q;struct nd_audio_request out;char path[129];
 nd_audio_queue_init(&q);assert(!nd_audio_queue_pop(&q,&out));
 assert(!nd_audio_queue_push(&q,NULL,0,0));assert(!nd_audio_queue_push(&q,"",0,0));
 assert(!nd_audio_queue_push(&q,"ok.wav",4,0));
 memset(path,'x',128);path[128]=0;assert(!nd_audio_queue_push(&q,path,0,0));
 path[127]=0;assert(nd_audio_queue_push(&q,path,0,0));
 assert(nd_audio_queue_pop(&q,&out) && strlen(out.path)==127);
 for(unsigned i=0;i<16;i++)assert(nd_audio_queue_push(&q,"alert.wav",ND_AUDIO_ALERT,0));
 assert(!nd_audio_queue_push(&q,"alert.wav",ND_AUDIO_ALERT,17));
 assert(q.count==16 && !q.evicted); /* ID0 means distinct requests. */
 nd_audio_queue_clear(&q);assert(!q.count && !nd_audio_queue_pop(&q,&out));
 return 0;
}''',['src/audio/queue.c'])
