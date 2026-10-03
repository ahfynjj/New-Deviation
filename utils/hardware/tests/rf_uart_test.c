#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
static struct {uint32_t a,v;} regs[100];
static unsigned used, writes, rx_left, rx_next, tx_n;
static uint8_t tx_bytes[128];
static int fail_ack;
static unsigned irq_depth;
static unsigned irq_lock(void) {return irq_depth++;}
static void irq_unlock(unsigned old) {assert(irq_depth==old+1);irq_depth=old;}
static uint32_t *reg(uint32_t a) {
    for(unsigned i=0;i<used;i++) if(regs[i].a==a) return &regs[i].v;
    assert(used<100); regs[used].a=a; return &regs[used++].v;
}
static uint32_t rd(uint32_t a) {
    if(a==0x4001141c) return (fail_ack?0:0x600000)|0xc0|(rx_left?0x20:0)|*reg(a);
    if(a==0x40011424) {assert(rx_left);rx_left--;return rx_next++ & 255;}
    return *reg(a);
}
static void wr(uint32_t a,uint32_t v) {
    writes++;
    if(a==0x40011428) {assert(tx_n<128);tx_bytes[tx_n++]=v;return;}
    if(a==0x40011420) {*reg(0x4001141c)&=~v;return;}
    if(a==0xe000e188) {*reg(0xe000e108)&=~v;return;}
    if(a==0xe000e288) {*reg(0xe000e208)&=~v;return;}
    if(a==0x58020418) {
        if(v&(1u<<13)) { /* power only after pins, baud and receiver configured */
            assert(*reg(0x4001140c)==80 && (*reg(0x40011400)&0x2d)==0x2d);
            assert((*reg(0x58021824)&0x0f0000f0)==0x07000070);
            assert(!(*reg(0x58021c14)&(1u<<9)));
        }
        *reg(0x58020414)=(*reg(0x58020414)|(v&65535))&~(v>>16);return;
    }
    if(a==0x58021c18) {*reg(0x58021c14)=(*reg(0x58021c14)|(v&65535))&~(v>>16);return;}
    *reg(a)=v;
}
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#define TX15_RF_BARRIER() ((void)0)
#define TX15_RF_LOCK() irq_lock()
#define TX15_RF_UNLOCK(old) irq_unlock(old)
#include "hardware/tx15/board/rf_uart.c"
static void reset(void) {
    memset(regs,0,sizeof(regs));used=writes=rx_left=rx_next=tx_n=0;fail_ack=0;
    *reg(0x58024418)=0x48;*reg(0x5802441c)=0x440;*reg(0x58024410)=0x1b;
}
int main(void) {
    reset(); *reg(0x580244f0)=32;
    assert(!tx15_rf_uart_init() && !writes);
    reset(); *reg(0x58024454)=8;
    assert(!tx15_rf_uart_init() && !writes);
    reset(); *reg(0x5802441c)=0;
    assert(!tx15_rf_uart_init() && !writes);
    reset(); *reg(0xe000e108)=128;
    assert(!tx15_rf_uart_init() && !writes);
    reset(); fail_ack=1;
    assert(!tx15_rf_uart_init());
    assert(!(*reg(0x58020414)&(1u<<13)) && !*reg(0x40011400));
    reset(); assert(tx15_rf_uart_init());
    assert(*reg(0x58020414)&(1u<<13));
    uint8_t data[65];for(unsigned i=0;i<65;i++) data[i]=i;
    assert(!tx15_rf_uart_send(data,65));
    assert(tx15_rf_uart_send(data,64));
    assert(irq_depth==0); /* Public send restores the caller's interrupt mask. */
    assert(!tx15_rf_uart_send(data,1));
    for(unsigned i=0;i<3;i++) USART6_IRQHandler();
    assert(tx_n==64 && !memcmp(tx_bytes,data,64));
    assert(!(*reg(0x40011400)&0x80));
    rx_left=300;
    for(unsigned i=0;i<10;i++) USART6_IRQHandler();
    assert(tx15_rf_uart_stats.rx_dropped==45);
    uint8_t v;for(unsigned i=0;i<255;i++) {assert(tx15_rf_uart_read(&v));assert(v==i);}
    assert(!tx15_rf_uart_read(&v));
    rx_left=5;USART6_IRQHandler();
    for(unsigned i=0;i<5;i++) {assert(tx15_rf_uart_read(&v));assert(v==(uint8_t)(300+i));}
    *reg(0x4001141c)=8;USART6_IRQHandler();
    assert(tx15_rf_uart_stats.errors==1);
    tx15_rf_uart_stop();
    assert(!*reg(0x40011400) && !(*reg(0xe000e108)&128));
    assert(!(*reg(0x58020414)&(1u<<13)));
    assert(!tx15_rf_uart_send(data,1));
    assert(tx15_rf_uart_init()); /* Module/model Off -> Internal must reopen. */
    assert(tx15_rf_uart_send(data,26));
    USART6_IRQHandler();assert(tx_n==90);
    tx15_rf_uart_stop();assert(!(*reg(0x580244f0)&32));
    puts("USART6 preconditions, power order, TX/RX bounds and stop PASS");
}
