/* TX15 MAX internal CRSF discovery UART; GPL-3.0-or-later.
 * Fixed board reference 19b50d967e6e579ac5a1b3bdb014b148a6b47491.
 * Warm RAM bootstrap only: PLL128/HCLK64/PCLK2=32MHz. 400000, 8N1,
 * full duplex, no inversion/DMA. IRQ71 drains into a bounded SPSC ring.
 * Caller must install the IRQ vector before init, and restore GPIO/RCC/NVIC
 * state using the bench recovery helper before resuming original firmware.
 */
#include "rf_uart.h"
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
#define U 0x40011400u
#define B 0x58020400u
#define G 0x58021800u
#define H 0x58021c00u
#define EN 0x580244f0u
#define RST 0x58024498u
#define ISER 0xe000e108u
#define ICER 0xe000e188u
#define ICPR 0xe000e288u
static uint8_t rx[256], tx[64];
static volatile unsigned rx_head, rx_tail, tx_pos, tx_size, active;
volatile struct tx15_rf_uart_stats tx15_rf_uart_stats;

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
    W(G+12,(R(G+12)&~(3u<<(pin*2)))|(1u<<(pin*2)));
    W(G+36,(R(G+36)&~(15u<<((pin-8)*4)))|(7u<<((pin-8)*4)));
    W(G,(R(G)&~(3u<<(pin*2)))|(2u<<(pin*2)));
}
void tx15_rf_uart_stop(void)
{
    uint32_t irq_mask=TX15_RF_LOCK();
    active=0;
    W(ICER,128); TX15_RF_BARRIER();
    if (R(EN)&32) {W(U,0);W(EN,R(EN)&~32u);(void)R(EN);}
    W(ICPR,128);
    W(B+24,1u<<29); /* PB13 power off, do not touch PH12 radio hold */
    TX15_RF_UNLOCK(irq_mask);
}
int tx15_rf_uart_init(void)
{
    if (active || (R(EN)&32) || (R(RST)&32) || (R(ISER)&128)
        || (R(0xe000e208u)&128) || (R(0xe000e308u)&128)
        || (R(0x58024410u)&0x3f)!=0x1b || (R(0x58024418u)&0xf7f)!=0x48
        || (R(0x5802441cu)&0x770)!=0x440 || (R(0x58024454u)&0x38)) return 0;
    W(0x580244e0u,R(0x580244e0u)|0xc2); (void)R(0x580244e0u);
    W(B+24,1u<<29); output(B,13);
    W(H+24,1u<<25); output(H,9); /* normal boot, not module bootloader */
    uart_pin(14); uart_pin(9);
    W(EN,R(EN)|32); (void)R(EN);
    W(RST,R(RST)|32); W(RST,R(RST)&~32u);
    W(U,0); W(U+4,0); W(U+8,0); W(U+44,0); W(U+12,80);
    rx_head=rx_tail=tx_pos=tx_size=0;
    tx15_rf_uart_stats=(struct tx15_rf_uart_stats){0};
    W(U+32,0x0f); W(U,0x2d); /* RE/TE/UE and RXNEIE; FIFO disabled */
    unsigned budget=100000;
    while ((R(U+28)&0x600000)!=0x600000) {
        if (!--budget) {tx15_rf_uart_stop();return 0;}
    }
    W(0xe000e444u,(R(0xe000e444u)&0x00ffffff)|0x40000000); /* IRQ71 priority */
    W(ICPR,128); active=1; W(ISER,128);
    W(B+24,1u<<13); /* enable module after receiver is ready */
    return 1;
}
static int send_locked(const uint8_t *data, unsigned size)
{
    if (!active || !data || !size || size>sizeof(tx) || tx_pos!=tx_size || !(R(U+28)&64)) return 0;
    memcpy(tx,data,size); tx_pos=0; tx_size=size;
    TX15_RF_BARRIER();
    W(U+32,64); W(U,R(U)|128); /* TXE interrupt publishes copied buffer */
    return 1;
}
int tx15_rf_uart_send(const uint8_t *data,unsigned size)
{
    uint32_t irq_mask=TX15_RF_LOCK();
    int accepted=send_locked(data,size);
    TX15_RF_UNLOCK(irq_mask);return accepted;
}
int tx15_rf_uart_read(uint8_t *value)
{
    if (!value || rx_tail==rx_head) return 0;
    TX15_RF_BARRIER(); *value=rx[rx_tail];
    TX15_RF_BARRIER(); rx_tail=(rx_tail+1)&255;
    return 1;
}
void USART6_IRQHandler(void)
{
    for (unsigned budget=0; budget<32; budget++) {
        uint32_t status=R(U+28);
        int worked=0;
        if (status&15) {tx15_rf_uart_stats.errors++;W(U+32,status&15);worked=1;}
        if (status&32) {
            uint8_t value=(uint8_t)R(U+36);
            tx15_rf_uart_stats.rx_bytes++;
            unsigned next=(rx_head+1)&255;
            if ((status&7) || next==rx_tail) tx15_rf_uart_stats.rx_dropped++;
            else {rx[rx_head]=value;TX15_RF_BARRIER();rx_head=next;}
            worked=1;
        }
        if ((status&128) && (R(U)&128)) {
            if (tx_pos<tx_size) {W(U+40,tx[tx_pos++]);tx15_rf_uart_stats.tx_bytes++;}
            if (tx_pos==tx_size) W(U,R(U)&~128u);
            worked=1;
        }
        if (!worked) break;
    }
}
