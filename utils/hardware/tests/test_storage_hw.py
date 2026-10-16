"""SDMMC1 register transport: read-only commands, IDMA and clock restoration."""
import unittest
import test_controls as controls
class StorageHardwareTests(unittest.TestCase):
    compile_run=controls.ControlsTests.compile_run
    def test_register_sequence_whitelist_async_read_and_shared_clock_restore(self):
        self.compile_run(r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "hardware/tx15/board/storage.h"
static uint32_t addresses[160],values[160],used;
static uint32_t *reg(uint32_t a){for(unsigned i=0;i<used;i++)if(addresses[i]==a)return &values[i];assert(used<160);addresses[used]=a;return &values[used++];}
static uint32_t rd(uint32_t a){return *reg(a);}
static void wr(uint32_t a,uint32_t v){
 assert(a!=0x58024400 && a!=0x58024428 && a!=0x58024430 && a!=0x58024438 && a!=0x58024440);
 assert(a<0x58001c00 || a>0x58001c28);assert(a!=0x52007080); /* No I2C or SD TX FIFO. */
 if(a==0x5802442c)assert(((v^rd(a))&~(1u<<17))==0);
 if(a==0x52007038)*reg(0x52007034)&=~v;
 *reg(a)=v;
}
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#define TX15_STORAGE_DMA_ADDRESS(p) ((uint32_t)0x24050000u)
#define TX15_STORAGE_BARRIER() ((void)0)
#include "hardware/tx15/board/storage.c"
int main(void){
 *reg(0x58024400)=0x3f030005;*reg(0x58024410)=0x1b;
 *reg(0x58024418)=0x48;*reg(0x58024428)=0x00c0c0c2; /* Audio M2/LCD M3 in use. */
 *reg(0x58024430)=0x0101023f;*reg(0x5802442c)=0x01090898;
 *reg(0x5802444c)=1u<<16;
 *reg(0x58020800)=0xaaaaaaaa;*reg(0x58020824)=0x87654321;
 *reg(0x58020c00)=0x55555555;*reg(0x58020c20)=0x12345678;
 uint32_t cfg=rd(0x5802442c),c_mode=rd(0x58020800),c_af=rd(0x58020824),d_mode=rd(0x58020c00),d_af=rd(0x58020c20);
 const struct nd_sd_ops *o=&tx15_storage_ops;
 assert(!o->init(NULL));assert(rd(0x52007004)==160 && rd(0x52007000)==3);
 assert((rd(0x5802442c)&(1u<<17)) && !(rd(0x5802444c)&(1u<<16)));
 unsigned n=used;assert(o->command(NULL,24,0,ND_SD_SHORT)<0 && used==n);
 assert(!o->command(NULL,8,0x1aa,ND_SD_SHORT));assert(rd(0x5200700c)==0x1108);
 uint32_t response[4];assert(!o->response(NULL,response)); /* No busy wait. */
 *reg(0x52007034)=64|0x2000;*reg(0x52007010)=8;*reg(0x52007014)=0x1aa;
 assert(!o->response(NULL,response)); /* Response flag can precede CPSM idle. */
 *reg(0x52007034)=64;
 assert(o->response(NULL,response)==1 && response[0]==0x1aa);
 assert(!o->command(NULL,41,0x40ff8000,ND_SD_OCR));
 *reg(0x52007034)=1|0x2000;*reg(0x52007014)=0xc0ff8000;
 assert(!o->response(NULL,response));
 *reg(0x52007034)=1;
 assert(o->response(NULL,response)==1); /* R3 contains no response CRC. */
 assert(!o->read_start(NULL,2048,1));assert(rd(0x52007008)==2048);
 assert(rd(0x52007028)==512 && rd(0x5200702c)==0x92 && rd(0x52007050)==1);
 assert(rd(0x52007058)==0x24050000 && rd(0x5200700c)==0x1151);
 *reg(0x52007034)=64;*reg(0x52007010)=17;*reg(0x52007014)=0x900;
 uint8_t out[512];memset(out,0,512);assert(!o->read_poll(NULL,out));
 for(unsigned i=0;i<128;i++)dma_buffer[i]=0x12345678;
 *reg(0x52007034)=0x500;*reg(0x52007030)=0;
 assert(o->read_poll(NULL,out)==1 && out[0]==0x78 && out[511]==0x12);
 assert(!o->read_start(NULL,2,0) && rd(0x52007008)==1024);
 o->stop(NULL);
 assert(rd(0x5802442c)==cfg && rd(0x5802444c)==(1u<<16));
 assert(rd(0x58020800)==c_mode && rd(0x58020824)==c_af && rd(0x58020c00)==d_mode && rd(0x58020c20)==d_af);
 assert(!(rd(0x580244d4)&(1u<<16)) && !rd(0x52007050));
 /* A live second SDMMC consumer prevents taking the shared kernel selector. */
 *reg(0x580244dc)=1u<<9;assert(o->init(NULL)<0);*reg(0x580244dc)=0;
 assert(!o->init(NULL));assert(o->read_start(NULL,0x800000,0)<0);o->stop(NULL);
 return 0;
}''',[])
