#include "settings_store.h"
#include <string.h>
#define MAGIC 0x4e445331u
#define COMMIT 0x434f4d54u
static uint32_t crc(uint32_t c,const void *p,unsigned n) {
 const unsigned char *v=p;
 while(n--) {c^=*v++;for(unsigned i=0;i<8;i++)c=(c>>1)^((0u-(c&1))&0xedb88320u);}return c;
}
static int payload(const struct tx15_store_io *io,unsigned base,const uint32_t *h) {
 unsigned char block[256];uint32_t c=~0u;
 for(unsigned p=0;p<h[4];) {
  unsigned n=h[4]-p;if(n>sizeof(block))n=sizeof(block);
  if(!io->read(io->ctx,base+32+p,block,n))return -1;
  c=crc(c,block,n);p+=n;
 }
 return ~c==h[5];
}
static int valid(const struct tx15_store_io *io,unsigned base,uint32_t *h) {
 if(!io->read(io->ctx,base,h,32))return -1;
 if(h[0]!=MAGIC || h[1]!=1 || h[7]!=COMMIT || !h[4] || h[4]>TX15_STORE_MAX_BYTES
   || h[6]!=~crc(~0u,h,24))return 0;
 return payload(io,base,h);
}
static int newest(int a,int b,const uint32_t *x,const uint32_t *y) {
 if(!a)return b?1:-1;
 if(!b)return 0;
 return (int32_t)(y[2]-x[2])>0?1:0;
}
int tx15_store_load(const struct tx15_store_io *io,unsigned id,void *out,unsigned n) {
 if(!io || !io->read || !out || !n || n>TX15_STORE_MAX_BYTES)return 0;
 uint32_t h[2][8];int a=valid(io,0,h[0]),b=valid(io,32768,h[1]);
 a=a>0 && h[0][3]==id && h[0][4]==n;b=b>0 && h[1][3]==id && h[1][4]==n;
 int slot=newest(a,b,h[0],h[1]);
 return slot>=0 && io->read(io->ctx,slot*32768u+32,out,n);
}
int tx15_store_save(const struct tx15_store_io *io,unsigned id,const void *data,unsigned n) {
 if(!io || !io->read || !io->erase || !io->program || !data || !n || n>TX15_STORE_MAX_BYTES)return 0;
 uint32_t old[2][8];int a=valid(io,0,old[0]),b=valid(io,32768,old[1]);
 if(a<0 || b<0)return 0;
 int previous=newest(a,b,old[0],old[1]);unsigned base=previous==0?32768:0;
 uint32_t h[8]={MAGIC,1,previous<0?1:old[previous][2]+1,id,n,~crc(~0u,data,n),0,~0u};
 h[6]=~crc(~0u,h,24);
 if(!io->erase(io->ctx,base) || !io->program(io->ctx,base,h,28)
   || !io->program(io->ctx,base+32,data,n))return 0;
 uint32_t check[8];
 if(!io->read(io->ctx,base,check,32) || memcmp(check,h,32) || payload(io,base,h)!=1)return 0;
 uint32_t commit=COMMIT;
 if(!io->program(io->ctx,base+28,&commit,4))return 0;
 return valid(io,base,check)==1;
}
