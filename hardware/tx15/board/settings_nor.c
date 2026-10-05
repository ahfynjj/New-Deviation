/* Native settings writer; explicit opt-in, not used by the cold loader. */
#ifdef TX15_PERSISTENCE
#include "settings_nor.h"
#include "settings_store.h"
#include "settings_clock.h"
#include "../boot/qspi.c"
#ifndef TX15_WRITE8
#define TX15_WRITE8(a,v) (*(volatile uint8_t *)(a)=(v))
#endif
extern uint32_t CLOCK_getms(void);
volatile uint32_t tx15_settings_status;
static int wait_status(uint32_t mask,uint32_t value) {
 uint32_t start=CLOCK_getms();
 for(unsigned n=0;n<1000000;n++) {
  uint32_t sr=TX15_READ32(QSPI+8);
  if(sr&0x11u)return 0;
  if((sr&mask)==value)return 1;
  if((uint32_t)(CLOCK_getms()-start)>=100)return 0;
 }return 0;
}
static int command(unsigned op,unsigned address,void *data,unsigned bytes,int read) {
 if(!wait_status(0x20,0))return 0;
 TX15_WRITE32(QSPI+12,0x1b);
 if(bytes)TX15_WRITE32(QSPI+16,bytes-1);
 uint32_t ccr=0x100u|op;
 if(address!=~0u)ccr|=0x2400;
 if(bytes)ccr|=0x1000000;
 if(bytes && read)ccr|=0x4000000;
 TX15_WRITE32(QSPI+20,ccr);
 if(address!=~0u)TX15_WRITE32(QSPI+24,address);
 unsigned char *p=data;
 for(unsigned i=0;i<bytes;i++) {
  uint32_t start=CLOCK_getms();int available=0;
  for(unsigned n=0;n<1000000;n++) {
   uint32_t sr=TX15_READ32(QSPI+8);if(sr&0x11)return 0;
   unsigned level=(sr>>8)&63;
   if(read ? level>0 : level<32) {available=1;break;}
   if((uint32_t)(CLOCK_getms()-start)>=100)return 0;
  }
  if(!available)return 0;
  if(read)p[i]=TX15_READ8(QSPI+32);else TX15_WRITE8(QSPI+32,p[i]);
 }
 if(!wait_status(0x22,2))return 0;
 TX15_WRITE32(QSPI+12,0x1b);return 1;
}
static int status(unsigned op,uint8_t *v) {return command(op,~0u,v,1,1);}
static int ready(unsigned timeout) {
 uint32_t start=CLOCK_getms();uint8_t v;
 for(unsigned n=0;n<100000;n++) {
  if(!status(5,&v))return 0;
  if(!(v&1))return 1;
  if((uint32_t)(CLOCK_getms()-start)>=timeout)return 0;
 }return 0;
}
static int enable_write(void) {
 uint8_t a,b,c;
 if(!status(5,&a) || !status(0x35,&b) || !status(0x15,&c)
   || a || (b&~0x02u) || (c&~0x60u))return 0;
 if(!command(6,~0u,0,0,0) || !status(5,&a))return 0;
 return (a&3)==2;
}
static int read_data(void *ctx,unsigned offset,void *out,unsigned n) {
 (void)ctx;
 return offset<65536 && n<=65536-offset
  && tx15_boot_qspi_read(TX15_SETTINGS_BASE+offset,out,n,1000000)==TX15_QSPI_OK;
}
static int erase_data(void *ctx,unsigned offset) {
 (void)ctx;if(offset!=0 && offset!=32768)return 0;
 for(unsigned p=0;p<32768;p+=4096) {
  if(!enable_write() || !command(0x20,TX15_SETTINGS_BASE+offset+p,0,0,0) || !ready(1000))return 0;
 }
 return 1;
}
static int program_data(void *ctx,unsigned offset,const void *data,unsigned n) {
 (void)ctx;if(!n || offset>=65536 || n>65536-offset)return 0;
 const unsigned char *p=data;
 while(n) {
  unsigned part=256-(offset&255);if(part>n)part=n;
  if(!enable_write() || !command(2,TX15_SETTINGS_BASE+offset,(void *)p,part,0) || !ready(50))return 0;
  offset+=part;p+=part;n-=part;
 }return 1;
}
static const struct tx15_store_io io={0,read_data,erase_data,program_data};
enum tx15_qspi_result settings_qspi_init(uint32_t *id,uint32_t budget)
{
    if (id) *id=0;
    if (!id || !budget || owned || (TX15_READ32(AHB3)&0x4000u)
            || (TX15_READ32(RESET)&0x4000u)
            || !tx15_settings_core_clock(TX15_READ32(0x58024400u))
            || (TX15_READ32(0x58024410u)&0x3fu)!=0x1bu
            || (TX15_READ32(0x58024418u)&0xf7fu)!=0x48u
            || (TX15_READ32(0x58024428u)&0x3f3u)!=0xc2u
            || (TX15_READ32(0x5802442cu)&0x7000fu)!=0x10008u
            || (TX15_READ32(0x58024430u)&0xffffu)!=0x23fu
            || (TX15_READ32(0x5802444cu)&0x30u)) return TX15_QSPI_BAD_STATE;
    TX15_WRITE32(AHB4,TX15_READ32(AHB4)|0x60u);(void)TX15_READ32(AHB4);
    /* Board AFs confirmed against this TX15's live GPIO readback. */
    TX15_WRITE32(0x58021818u,1u<<6);
    pin(0x58021800u,6,10);
    for (unsigned n=6;n<=10;n++) pin(0x58021400u,n,n==8||n==9?10:9);
    TX15_WRITE32(AHB3,TX15_READ32(AHB3)|0x4000u);(void)TX15_READ32(AHB3);
    owned=1;identified=0;
    modify(RESET,0x4000u,0x4000u);modify(RESET,0x4000u,0);
    TX15_WRITE32(QSPI+4,0x00170300u); // 16MiB address window, CS high 4 cycles
    TX15_WRITE32(QSPI,0x0f000001u); // HCLK64 / 16 = 4MHz; FIFO threshold 1
    uint8_t bytes[3];
    enum tx15_qspi_result result=receive(0x9f,0,bytes,3,budget);
    if (result!=TX15_QSPI_OK) return result;
    uint32_t value=(uint32_t)bytes[0]<<16|(uint32_t)bytes[1]<<8|bytes[2];
    if (!bytes[0] || bytes[0]==0xff || !bytes[2] || bytes[2]==0xff) return TX15_QSPI_BAD_ID;
    *id=value;identified=1;return TX15_QSPI_OK;
}
static int start(void) {
 uint32_t id=0;
 tx15_settings_status=1;
 if(settings_qspi_init(&id,1000000)!=TX15_QSPI_OK || id!=0xc84018u) {
  tx15_boot_qspi_stop();tx15_settings_status=4;return 0;
 }return 1;
}
int tx15_settings_load(unsigned model,void *data,unsigned n) {
 if(model!=1 || !start())return 0;
 int ok=tx15_store_load(&io,1,data,n);tx15_boot_qspi_stop();
 tx15_settings_status=ok?2:3;return ok;
}
int tx15_settings_save(unsigned model,const void *data,unsigned n) {
 if(model!=1 || !start())return 0;
 int ok=tx15_store_save(&io,1,data,n);tx15_boot_qspi_stop();
 tx15_settings_status=ok?2:4;return ok;
}
#endif
