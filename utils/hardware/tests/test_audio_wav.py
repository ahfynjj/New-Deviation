"""Portable incremental WAV validation; no board or filesystem required."""
import unittest
import test_controls as controls

COMMON=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "src/audio/wav.h"
static uint8_t b[4096];
static void u16(unsigned p,unsigned v){b[p]=v;b[p+1]=v>>8;}
static void u32(unsigned p,uint32_t v){for(unsigned i=0;i<4;i++)b[p+i]=v>>(8*i);}
static unsigned make(unsigned bits,unsigned rate){
 memset(b,0,sizeof(b));memcpy(b,"RIFF",4);memcpy(b+8,"WAVEfmt ",8);
 u32(16,16);u16(20,1);u16(22,1);u32(24,rate);
 u32(28,rate*bits/8);u16(32,bits/8);u16(34,bits);
 memcpy(b+36,"data",4);unsigned bytes=bits/8*5;u32(40,bytes);
 unsigned n=44+bytes+(bytes&1);u32(4,n-8);return n;
}
static int scan(unsigned n,unsigned slice,struct nd_wav *w){
 nd_wav_init(w,n);unsigned offset=0;
 while(offset<n && w->status==ND_WAV_MORE){
  size_t used=999;unsigned count=n-offset;if(count>slice)count=slice;
  int status=nd_wav_feed(w,b+offset,count,&used);
  assert(used<=count && used<=ND_WAV_FEED_LIMIT);
  assert(used || status!=ND_WAV_MORE);offset+=(unsigned)used;
 }
 if(w->status==ND_WAV_MORE)nd_wav_finish(w);
 return w->status;
}
'''

class AudioWavTests(unittest.TestCase):
    compile_run=controls.ControlsTests.compile_run
    def test_fragmented_chunks_padding_and_supported_pcm_formats(self):
        self.compile_run(COMMON+r'''
int main(void){
 struct nd_wav w;assert(sizeof(w)<=96);
 const unsigned rates[]={8000,16000,32000};
 for(unsigned r=0;r<3;r++)for(unsigned bits=8;bits<=16;bits+=8){
  unsigned n=make(bits,rates[r]);
  for(unsigned slice=1;slice<=60;slice++){
   assert(scan(n,slice,&w)==ND_WAV_DATA);
   assert(w.format.rate==rates[r] && w.format.bits==bits && w.format.frames==5);
   assert(w.format.data_offset==44 && w.format.data_bytes==5*bits/8);
  }
 }
 unsigned n=make(16,32000);
 /* Long metadata before fmt: no whole-file buffering or fixed 44-byte head. */
 memmove(b+12+2056,b+12,n-12);memcpy(b+12,"JUNK",4);u32(16,2048);
 memset(b+20,0xaa,2048);n+=2056;u32(4,n-8);
 assert(scan(n,513,&w)==ND_WAV_DATA && w.format.data_offset==2100);
 n=make(8,16000);memmove(b+24,b+12,n-12);memcpy(b+12,"LIST",4);u32(16,3);
 b[20]=1;b[21]=2;b[22]=3;b[23]=0;n+=12;u32(4,n-8);
 assert(scan(n,1,&w)==ND_WAV_DATA && w.format.data_offset==56);
 /* PCM fmt extension with cbSize=0 is accepted. */
 n=make(16,32000);memmove(b+38,b+36,n-36);u16(36,0);u32(16,18);n+=2;u32(4,n-8);
 assert(scan(n,1,&w)==ND_WAV_DATA && w.format.data_offset==46);
 return 0;
}''',['src/audio/wav.c'])

    def test_malformed_lengths_formats_and_partial_headers_are_rejected(self):
        self.compile_run(COMMON+r'''
int main(void){
 struct nd_wav w;unsigned n;
 n=make(16,32000);b[0]='X';assert(scan(n,1,&w)<0);
 n=make(16,32000);b[8]='X';assert(scan(n,2,&w)<0);
 n=make(16,32000);u32(4,0xffffffff);assert(scan(n,512,&w)<0);
 n=make(16,32000);u32(16,0xffffffff);assert(scan(n,512,&w)<0);
 n=make(16,32000);u32(40,0xffffffff);assert(scan(n,512,&w)<0);
 n=make(16,32000);u32(40,9);assert(scan(n,512,&w)<0); /* Half sample. */
 n=make(16,32000);u32(40,0);assert(scan(n,512,&w)<0);
 n=make(16,32000);u16(20,3);assert(scan(n,512,&w)<0); /* Float. */
 n=make(16,32000);u16(22,2);assert(scan(n,512,&w)<0);
 n=make(16,44100);assert(scan(n,512,&w)<0);
 n=make(16,32000);u32(28,1);assert(scan(n,512,&w)<0);
 n=make(16,32000);u16(32,1);assert(scan(n,512,&w)<0);
 n=make(16,32000);u16(34,24);assert(scan(n,512,&w)<0);
 n=make(16,32000);u32(16,17);assert(scan(n,512,&w)<0);
 n=make(16,32000);memcpy(b+12,"data",4);assert(scan(n,512,&w)<0);
 n=make(8,32000);u32(4,n-9);assert(scan(n,512,&w)<0); /* Missing odd pad. */
 n=make(16,32000);
 for(unsigned cut=0;cut<44;cut++){
  nd_wav_init(&w,n);size_t used=0;nd_wav_feed(&w,b,cut,&used);
  assert(nd_wav_finish(&w)<0);
 }
 /* A smaller declared file may never cause an out-of-range data read. */
 for(unsigned cut=0;cut<n;cut++)assert(scan(cut,512,&w)<0);
 return 0;
}''',['src/audio/wav.c'])
