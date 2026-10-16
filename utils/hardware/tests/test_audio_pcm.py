"""Streaming PCM conversion has bounded output, split frames and exact tails."""
import unittest
import test_controls as controls
COMMON=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "src/audio/pcm.h"
static inline void convert(const uint8_t *src,unsigned bytes,unsigned bits,unsigned rate,
                    const int16_t *expected,unsigned frames,unsigned slice,unsigned capacity){
 struct nd_wav_format f={.rate=rate,.bits=bits,.align=bits/8,.data_bytes=bytes,.frames=bytes/(bits/8)};
 struct nd_pcm c;assert(!nd_pcm_init(&c,&f));assert(sizeof(c)<=64);
 unsigned pos=0,total=0,iterations=0;
 while(c.status!=ND_PCM_DONE){
  assert(++iterations<1000);int16_t out[300];for(unsigned i=0;i<300;i++)out[i]=123;
  size_t used=999,written=999;unsigned n=bytes-pos;if(n>slice)n=slice;
  int result=nd_pcm_process(&c,src+pos,n,&used,out,capacity,&written);
  assert(result>=0 && used<=n && used<=ND_PCM_INPUT_LIMIT);
  assert(written<=capacity && written<=ND_PCM_OUTPUT_LIMIT && out[written]==123);
  assert(used || written || result==ND_PCM_DONE);
  for(size_t i=0;i<written;i++){assert(total<frames);assert(out[i]==expected[total++]);}
  pos+=(unsigned)used;
 }
 assert(pos==bytes && total==frames && nd_pcm_finish(&c)==ND_PCM_DONE);
}
'''
class AudioPcmTests(unittest.TestCase):
    compile_run=controls.ControlsTests.compile_run
    def test_pcm_extremes_split_frames_and_linear_upsampling(self):
        self.compile_run(COMMON+r'''
int main(void){
 const uint8_t raw16[]={0,128,255,255,0,0,1,0,255,127};
 const int16_t direct[]={-32768,-1,0,1,32767};
 const uint8_t raw8[]={0,128,255};const int16_t signed8[]={-32768,0,32512};
 const uint8_t ramp[]={0,0,0,64};
 const int16_t twice[]={0,8192,16384,16384};
 const int16_t four[]={0,4096,8192,12288,16384,16384,16384,16384};
 for(unsigned s=1;s<=12;s++)for(unsigned cap=1;cap<=10;cap++){
  convert(raw16,sizeof(raw16),16,32000,direct,5,s,cap);
  convert(raw8,sizeof(raw8),8,32000,signed8,3,s,cap);
  convert(ramp,sizeof(ramp),16,16000,twice,4,s,cap);
  convert(ramp,sizeof(ramp),16,8000,four,8,s,cap);
 }
 return 0;
}''',['src/audio/pcm.c'])

    def test_truncation_output_backpressure_and_invalid_format(self):
        self.compile_run(COMMON+r'''
int main(void){
 struct nd_wav_format f={.rate=32000,.bits=16,.align=2,.data_bytes=2,.frames=1};
 struct nd_pcm c;int16_t out[300];size_t used,written;uint8_t raw[]={0,128,77};
 assert(!nd_pcm_init(&c,&f));
 assert(nd_pcm_process(&c,raw,2,&used,out,0,&written)==ND_PCM_MORE && !used && !written);
 assert(nd_pcm_process(&c,raw,1,&used,out,1,&written)==ND_PCM_MORE && used==1 && !written);
 assert(nd_pcm_finish(&c)==ND_PCM_TRUNCATED);
 assert(nd_pcm_process(&c,raw+1,1,&used,out,1,&written)==ND_PCM_TRUNCATED);
 assert(!nd_pcm_init(&c,&f));
 assert(nd_pcm_process(&c,raw,3,&used,out,300,&written)==ND_PCM_DONE);
 assert(used==2 && written==1 && out[0]==-32768); /* Do not consume RIFF padding/tail. */
 f.rate=44100;assert(nd_pcm_init(&c,&f)<0);f.rate=32000;
 f.frames=2;assert(nd_pcm_init(&c,&f)<0);f.frames=1;
 f.data_bytes=1;assert(nd_pcm_init(&c,&f)<0);f.data_bytes=2;
 f.align=1;assert(nd_pcm_init(&c,&f)<0);f.align=2;
 /* Long input: output limit applies even with a large destination. */
 uint8_t many[1024];memset(many,128,sizeof(many));
 f.bits=8;f.align=1;f.frames=f.data_bytes=1024;
 assert(!nd_pcm_init(&c,&f));
 assert(nd_pcm_process(&c,many,sizeof(many),&used,out,300,&written)==ND_PCM_MORE);
 assert(written==ND_PCM_OUTPUT_LIMIT && used<=ND_PCM_INPUT_LIMIT);
 return 0;
}''',['src/audio/pcm.c'])
