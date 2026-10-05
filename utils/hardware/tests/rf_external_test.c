#include <assert.h>
#include <stdint.h>
#include <string.h>
static struct {uint32_t a,v;} regs[64];static unsigned used,count;static int transmitting;
static uint32_t *reg(uint32_t a) {for(unsigned i=0;i<used;i++)if(regs[i].a==a)return &regs[i].v;assert(used<64);regs[used].a=a;return &regs[used++].v;}
static uint32_t rd(uint32_t a) {if(a==0x4001101c)return *reg(a)|0x600080;return *reg(a);}
static void wr(uint32_t a,uint32_t v) {
 if(a==0x40011028) {count++;transmitting=1;return;}
 if(a==0x40011020) {*reg(0x4001101c)&=~v;return;}
 if(a==0x58020c18 && v==16) {
  assert(*reg(0x4001100c)==80 && *reg(0x40011004)==0x30000 && *reg(0x40011008)==8);
 }
 *reg(a)=v;
}
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#define TX15_RF_BARRIER() ((void)0)
#define TX15_RF_LOCK() 0u
#define TX15_RF_UNLOCK(v) ((void)(v))
#include "hardware/tx15/board/rf_external.c"
int main(void) {
 *reg(0x58024410)=0x1b;*reg(0x58024418)=0x48;*reg(0x5802441c)=0x440;
 *reg(0x4001101c)=64;assert(tx15_rf_external_init());
 assert(((*reg(0x58020c00)>>8)&3)==1 && !(*reg(0x58020c04)&16));
 assert(*reg(0x58020024)==0x70 && *reg(0x58020c18)==16);
 uint8_t frame[3]={1,2,3};assert(tx15_rf_external_send(frame,3));
 assert(!(*reg(0x40011000)&4));
 USART1_IRQHandler();assert(transmitting && count==3);
 assert(*reg(0x40011000)&64);assert(!tx15_rf_external_send(frame,3));
 *reg(0x4001101c)|=64;USART1_IRQHandler();
 assert((*reg(0x40011000)&(4|8|64))==4);
 assert(tx15_rf_external_send(frame,3));
 tx15_rf_external_stop();assert(*reg(0x58020c18)==(1u<<20));
 assert(!tx15_rf_external_send(frame,3));
}
