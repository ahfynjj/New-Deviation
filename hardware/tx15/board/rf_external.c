/* TX15 external ELRS: USART1 PA9 S.PORT, PD4 power, inverted single-wire.
 * GPIO/route facts from fixed official module_ports + TX15 hal definitions.
 * Register-model verified; external-module hardware acceptance is pending. */
#include "rf_external.h"
#include <string.h>
#ifndef TX15_READ32
#define TX15_READ32(a) (*(volatile uint32_t *)(a))
#define TX15_WRITE32(a,v) (*(volatile uint32_t *)(a)=(v))
#endif
#ifndef TX15_RF_BARRIER
#define TX15_RF_BARRIER() __asm volatile("dmb" ::: "memory")
#endif
#ifndef TX15_RF_LOCK
static uint32_t irq_lock(void) {
    uint32_t old;__asm volatile("mrs %0,primask\ncpsid i":"=r"(old)::"memory");return old;
}
static void irq_unlock(uint32_t old) {__asm volatile("msr primask,%0"::"r"(old):"memory");}
#define TX15_RF_LOCK() irq_lock()
#define TX15_RF_UNLOCK(old) irq_unlock(old)
#endif
#define R(a) TX15_READ32(a)
#define W(a,v) TX15_WRITE32(a,v)
#define U 0x40011000u
#define B 0x58020c00u
#define G 0x58020000u
#define H 0x58021c00u
#define EN 0x580244f0u
#define RST 0x58024498u
#define ISER 0xe000e104u
#define ICER 0xe000e184u
#define ICPR 0xe000e284u
static uint8_t rx[256], tx[64];
static volatile unsigned rx_head, rx_tail, tx_pos, tx_size, active;
volatile struct tx15_rf_uart_stats tx15_rf_external_stats;

static void output(uint32_t port, unsigned pin)
{
    W(port+4,R(port+4)&~(1u<<pin));
    W(port+12,R(port+12)&~(3u<<(pin*2)));
    W(port,(R(port)&~(3u<<(pin*2)))|(1u<<(pin*2)));
}
static void uart_pin(unsigned pin)
{
    W(G+4,R(G+4)&~(1u<<pin));
    W(G+8,(R(G+8)&~(3u<<(pin*2)))|(2u<<(pin*2)));
    W(G+12,(R(G+12)&~(3u<<(pin*2)))|(2u<<(pin*2)));
    W(G+36,(R(G+36)&~(15u<<((pin-8)*4)))|(7u<<((pin-8)*4)));
    W(G,(R(G)&~(3u<<(pin*2)))|(2u<<(pin*2)));
}
void tx15_rf_external_stop(void)
{
    uint32_t irq_mask=TX15_RF_LOCK();
    active=0;
    W(ICER,32); TX15_RF_BARRIER();
    if (R(EN)&16) {W(U,0);W(EN,R(EN)&~16u);(void)R(EN);}
    W(ICPR,32);
    W(B+24,1u<<20); /* PB13 power off, do not touch PH12 radio hold */
    TX15_RF_UNLOCK(irq_mask);
}
int tx15_rf_external_init(void)
{
    if (active || (R(EN)&16) || (R(RST)&16) || (R(ISER)&32)
        || (R(0xe000e204u)&32) || (R(0xe000e304u)&32)
        || (R(0x58024410u)&0x3f)!=0x1b || (R(0x58024418u)&0xf7f)!=0x48
        || (R(0x5802441cu)&0x770)!=0x440 || (R(0x58024454u)&0x38)) return 0;
    W(0x580244e0u,R(0x580244e0u)|0x9); (void)R(0x580244e0u);
    W(B+24,1u<<20); output(B,4);
    uart_pin(9);
    W(EN,R(EN)|16); (void)R(EN);
    W(RST,R(RST)|16); W(RST,R(RST)&~16u);
    W(U,0); W(U+4,0x30000); W(U+8,8); W(U+44,0); W(U+12,80);
    rx_head=rx_tail=tx_pos=tx_size=0;
    tx15_rf_external_stats=(struct tx15_rf_uart_stats){0};
    W(U+32,0x0f); W(U,0x25); /* RE/TE/UE and RXNEIE; FIFO disabled */
    unsigned budget=100000;
    while ((R(U+28)&0x400000)!=0x400000) {
        if (!--budget) {tx15_rf_external_stop();return 0;}
    }
    W(0xe000e424u,(R(0xe000e424u)&0xffff00ff)|0x4000); /* IRQ37 priority */
    W(ICPR,32); active=1; W(ISER,32);
    W(B+24,1u<<4); /* enable module after receiver is ready */
    return 1;
}
static int send_locked(const uint8_t *data, unsigned size)
{
    if (!active || !data || !size || size>sizeof(tx) || tx_pos!=tx_size || (R(U)&64) || !(R(U+28)&64)) return 0;
    memcpy(tx,data,size); tx_pos=0; tx_size=size;
    TX15_RF_BARRIER();
    W(U+24,8); W(U+32,64); W(U,(R(U)&~4u)|8u|128u); /* TXE interrupt publishes copied buffer */
    return 1;
}
int tx15_rf_external_send(const uint8_t *data,unsigned size)
{
    uint32_t irq_mask=TX15_RF_LOCK();
    int accepted=send_locked(data,size);
    TX15_RF_UNLOCK(irq_mask);return accepted;
}
int tx15_rf_external_read(uint8_t *value)
{
    if (!value || rx_tail==rx_head) return 0;
    TX15_RF_BARRIER(); *value=rx[rx_tail];
    TX15_RF_BARRIER(); rx_tail=(rx_tail+1)&255;
    return 1;
}
void USART1_IRQHandler(void)
{
    for (unsigned budget=0; budget<32; budget++) {
        uint32_t status=R(U+28);
        int worked=0;
        if (status&15) {tx15_rf_external_stats.errors++;W(U+32,status&15);worked=1;}
        if (status&32) {
            uint8_t value=(uint8_t)R(U+36);
            tx15_rf_external_stats.rx_bytes++;
            unsigned next=(rx_head+1)&255;
            if ((status&7) || next==rx_tail) tx15_rf_external_stats.rx_dropped++;
            else {rx[rx_head]=value;TX15_RF_BARRIER();rx_head=next;}
            worked=1;
        }
        if ((status&128) && (R(U)&128)) {
            if (tx_pos<tx_size) {W(U+40,tx[tx_pos++]);tx15_rf_external_stats.tx_bytes++;}
            if (tx_pos==tx_size) W(U,(R(U)&~128u)|64u);
            worked=1;
        }
        if ((status&64) && (R(U)&64)) {
            W(U,(R(U)&~(8u|64u))|4u);worked=1;
        }
        if (!worked) break;
    }
}
