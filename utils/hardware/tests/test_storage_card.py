"""Cooperative SD identification/read-only metadata with fake transport."""
import unittest
import test_controls as controls
COMMON=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "src/storage/card.h"
struct fake {unsigned cmd,arg,starts,stops,reads,legacy,ocr_attempts,hang,bad_crc,bad_echo,missing_app;};
static int init(void *p){((struct fake*)p)->starts++;return 0;}
static void stop(void *p){((struct fake*)p)->stops++;}
static int command(void *p,unsigned cmd,uint32_t arg,unsigned response){
 struct fake *f=p;assert(response<=ND_SD_LONG);f->cmd=cmd;f->arg=arg;
 assert(cmd==0 || cmd==8 || cmd==55 || cmd==41 || cmd==2 || cmd==3 || cmd==9 || cmd==7 || cmd==13 || cmd==16);
 if(cmd==8)assert(arg==0x1aa);
 if(cmd==16)assert(arg==512);
 return 0;
}
static int response(void *p,uint32_t out[4]){
 struct fake *f=p;memset(out,0,16);if(f->hang)return 0;if(f->bad_crc)return ND_SD_CRC;
 switch(f->cmd){
 case 8:if(f->legacy)return ND_SD_TIMEOUT;out[0]=f->bad_echo?0x1ab:0x1aa;break;
 case 55:out[0]=f->missing_app?0:0x20;break;
 case 41:out[0]=0x00ff8000|(++f->ocr_attempts>1?0x80000000u:0)|(f->legacy?0:0x40000000);break;
 case 2:out[0]=0x12345678;out[3]=0xab;break;
 case 3:out[0]=0x12340000;break;
 case 9:
  if(f->legacy){out[1]=(9u<<16)|1023;out[2]=(3u<<30)|(7u<<15);}
  else {out[0]=1u<<30;out[2]=0x7fff0000;}
  break;
 case 7:case 13:case 16:out[0]=0x900;break;
 }
 return 1;
}
static int read_start(void *p,uint32_t lba,int hc){struct fake *f=p;f->arg=lba;f->reads++;assert(hc==!f->legacy);return 0;}
static void w16(uint8_t *b,unsigned n,unsigned v){b[n]=v;b[n+1]=v>>8;}
static void w32(uint8_t *b,unsigned n,uint32_t v){for(unsigned i=0;i<4;i++)b[n+i]=v>>(8*i);}
static int read_poll(void *p,uint8_t b[512]){
 struct fake *f=p;if(f->hang)return 0;memset(b,0,512);w16(b,510,0xaa55);
 if(!f->legacy && !f->arg){b[450]=0x0c;w32(b,454,2048);w32(b,458,1048576);return 1;}
 assert(f->arg==(f->legacy?0:2048));
 b[0]=0xeb;w16(b,11,512);b[13]=8;w16(b,14,32);b[16]=2;
 w32(b,32,1048576);w32(b,36,1024);w32(b,44,2);return 1;
}
static const struct nd_sd_ops ops={init,stop,command,response,read_start,read_poll};
static void run(struct nd_card *c,uint32_t start){for(unsigned i=0;i<2200 && c->report.state==ND_CARD_BUSY;i++)nd_card_poll(c,start+i);}
'''
class StorageCardTests(unittest.TestCase):
    compile_run=controls.ControlsTests.compile_run
    def test_sdhc_and_legacy_sd_capacity_and_readonly_volume_scan(self):
        self.compile_run(COMMON+r'''
int main(void){
 struct fake f={0};struct nd_card c={0};
 assert(nd_card_begin(&c,&ops,&f,0));assert(c.report.state==ND_CARD_BUSY);run(&c,0);
 assert(c.report.state==ND_CARD_READY && !c.report.error && c.report.high_capacity);
 assert(c.report.blocks==33554432ull && c.report.rca==0x1234 && c.report.cid[0]==0x12345678);
 assert(c.report.volume.fs==ND_FS_FAT32 && c.report.volume.lba==2048 && f.reads==2 && f.stops==1);
 nd_card_stop(&c);assert(c.report.state==ND_CARD_OFF);
 memset(&f,0,sizeof(f));f.legacy=1;assert(nd_card_begin(&c,&ops,&f,0xfffffff0u));run(&c,0xfffffff0u);
 assert(c.report.state==ND_CARD_READY && !c.report.high_capacity && c.report.blocks==2097152);
 assert(f.reads==1 && c.report.volume.lba==0);
 uint32_t csd[4]={2u<<30,0,0,0};uint64_t blocks;
 assert(!nd_card_capacity(csd,&blocks));return 0;
}''',['src/storage/card.c','src/storage/volume.c'])

    def test_timeout_bad_echo_crc_and_wrong_protocol_stop_without_writes(self):
        self.compile_run(COMMON+r'''
int main(void){
 for(unsigned mode=0;mode<4;mode++){
  struct fake f={0};struct nd_card c={0};
  f.hang=mode==0;f.bad_echo=mode==1;f.bad_crc=mode==2;f.missing_app=mode==3;
  assert(nd_card_begin(&c,&ops,&f,0));run(&c,0);
  assert(c.report.state==ND_CARD_ERROR && c.report.error && f.stops==1 && !f.reads);
 }
 struct fake f={0};struct nd_card c={0};assert(nd_card_begin(&c,&ops,&f,0));
 nd_card_stop(&c);run(&c,0);assert(!f.reads && c.report.state==ND_CARD_OFF);
 return 0;
}''',['src/storage/card.c','src/storage/volume.c'])
