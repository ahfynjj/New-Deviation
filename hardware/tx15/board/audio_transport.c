/* Native STM32H750 I2S2/DMA1 stream4. Register facts: ST stm32h750xx.h
 * and ST HAL I2S v1.11.2; TX15 pin facts recorded in audio-notes.md.
 * Buffers are application-initialized D2 SRAM, caches/MPU off.
 * GPL-3.0-or-later. */
#include "audio.h"
#include "audio_memory.h"
#ifndef TX15_READ32
#define TX15_READ32(a) (*(volatile uint32_t *)(a))
#define TX15_WRITE32(a,v) (*(volatile uint32_t *)(a)=(v))
#endif
#ifndef TX15_AUDIO_WORD
#define TX15_AUDIO_WORD(a) (*(volatile uint32_t *)(a))
#endif
#ifndef TX15_AUDIO_BARRIER
#define TX15_AUDIO_BARRIER() __asm volatile("dmb" ::: "memory")
#endif
#define R(a) TX15_READ32(a)
#define W(a,v) TX15_WRITE32(a,v)
#define RCC 0x58024400u
#define SPI 0x40003800u
#define DMA 0x40020070u
static unsigned owned,running,configured,phase,produced,fault;
static volatile unsigned ready[2],remaining;
static void modify(uint32_t a,uint32_t mask,uint32_t value) {W(a,(R(a)&~mask)|value);}
static void pin(uint32_t port,unsigned n) {
    modify(port+4,1u<<n,0);modify(port+8,3u<<(n*2),2u<<(n*2));
    modify(port+12,3u<<(n*2),0);
    modify(port+0x20+(n/8)*4,15u<<((n%8)*4),5u<<((n%8)*4));
    modify(port,3u<<(n*2),2u<<(n*2));
}
void tx15_audio_reset_pin(unsigned high) {
    modify(RCC+0xe0,0,1u<<7);(void)R(RCC+0xe0);
    W(0x58021c18u,1u<<(high?10:26));
    modify(0x58021c04u,1u<<10,0);modify(0x58021c0cu,3u<<20,0);
    modify(0x58021c00u,3u<<20,1u<<20);
}
int tx15_audio_transport_init(void) {
    /* Refuse to take a live PLL2, SPI2 or stream from another owner. */
    if(owned || (R(RCC)&0x0c000000u) || (R(RCC+0xe8)&0x4000u)
       || (R(DMA)&1) || (R(0xe000ed14u)&0x30000u) || (R(0xe000ed94u)&1))return -1;
    owned=1;configured=running=fault=0;remaining=0;ready[0]=ready[1]=0;
    /* HSE48/M12 * (98+2490/8192) / P8 = 49.1519775MHz.
     * MCLK = kernel/6 = 8.191996MHz; Fs=MCLK/256=31999.985Hz. */
    modify(RCC+0x28,0x3f000u,12u<<12);
    modify(RCC+0x2c,0x3800f0u,0x80080u);
    W(RCC+0x38,(1u<<24)|(1u<<16)|(7u<<9)|97u);
    W(RCC+0x3c,2490u<<3);modify(RCC+0x2c,0,1u<<4);
    modify(RCC,0,1u<<26);return 0;
}
int tx15_audio_transport_ready(void) {
    if(!owned || fault)return -1;
    if(!(R(RCC)&(1u<<27)))return 0;
    if(configured)return 1;
    modify(RCC+0x50,7u<<12,1u<<12); /* SPI123 kernel = PLL2P. */
    modify(RCC+0xe0,0,(1u<<2)|(1u<<8));(void)R(RCC+0xe0);
    pin(0x58020800u,6);pin(0x58022000u,0);pin(0x58022000u,1);pin(0x58022000u,3);
    modify(RCC+0xd8,0,1);(void)R(RCC+0xd8); /* DMA1 (DMAMUX1 shares DMA clock). */
    modify(RCC+0xe8,0,1u<<14);(void)R(RCC+0xe8);
    modify(RCC+0x90,0,1u<<14);modify(RCC+0x90,1u<<14,0);
    W(SPI,0);W(SPI+4,0);W(SPI+8,0);W(SPI+12,1u<<31);W(SPI+16,0);
    W(SPI+0x18,0x0ff8);W(SPI+0x50,0x02030005u);
    /* Master transmit, Philips I2S, 16-bit/16-bit channels, MCLK enabled. */
    for(unsigned i=0;i<1024;i++)TX15_AUDIO_WORD(TX15_AUDIO_DMA_BASE+4*i)=0;
    W(DMA,0);W(DMA+4,1024);W(DMA+8,SPI+0x20);
    W(DMA+12,TX15_AUDIO_DMA_BASE);W(DMA+16,TX15_AUDIO_DMA_BASE+2048);W(DMA+20,0);
    W(0x40020810u,40); /* DMAMUX1 channel4 = SPI2_TX. */
    W(0x4002000cu,0x3du);W(0xe000e280u,1u<<15);
    modify(0xe000e40cu,0xff000000u,0xa0000000u); /* Lower priority than RF. */
    configured=1;return 1;
}
void tx15_audio_transport_start(void) {
    if(!configured || running)return;
    TX15_AUDIO_BARRIER();
    W(0xe000e100u,1u<<15);
    W(DMA,(1u<<18)|(1u<<16)|(1u<<13)|(1u<<11)|(1u<<10)|(1u<<8)|
          (1u<<6)|(1u<<4)|(1u<<2)|(1u<<1)|1u);
    W(SPI+8,1u<<15);W(SPI,1);W(SPI,0x201);running=1;
}
int tx15_audio_transport_tone(unsigned frames) {
    if(!running || remaining || ready[0] || ready[1])return 0;
    produced=phase=0;remaining=frames;return 1;
}
void tx15_audio_transport_poll(unsigned now) {
    (void)now;
    if(!running)return;
    for(unsigned half=0;half<2;half++)if(!ready[half] && remaining) {
        for(unsigned i=0;i<TX15_AUDIO_HALF_WORDS;i++) {
            int sample=0;
            if(remaining) {
                sample=((int)(phase<16?phase:32-phase)*1024)-8192;
                unsigned envelope=produced<64?produced:remaining<64?remaining:64;
                sample=sample*(int)envelope/64;
                phase=(phase+1)&31;produced++;remaining--;
            }
            uint32_t v=(uint16_t)sample;
            TX15_AUDIO_WORD(TX15_AUDIO_PCM_BASE+half*2048+i*4)=v|(v<<16);
        }
        TX15_AUDIO_BARRIER();ready[half]=1;
    }
}
void DMA1_Stream4_IRQHandler(void) {
    uint32_t flags=R(0x40020004u)&0x3du;
    W(0x4002000cu,flags);
    if(!running)return;
    if(flags&0x0du) { /* FIFO/direct-mode/transfer error: mute, defer cleanup. */
        tx15_audio_report.errors++;fault=1;running=0;W(SPI,0);modify(DMA,1,0);
        W(0x58021c18u,1u<<26);return;
    }
    if(!(flags&32))return;
    unsigned half=(R(DMA)&(1u<<19))?0:1,filled=ready[half];
    TX15_AUDIO_BARRIER();
    for(unsigned i=0;i<TX15_AUDIO_HALF_WORDS;i++) {
        uint32_t value=filled?TX15_AUDIO_WORD(TX15_AUDIO_PCM_BASE+half*2048+i*4):0;
        TX15_AUDIO_WORD(TX15_AUDIO_DMA_BASE+half*2048+i*4)=value;
    }
    TX15_AUDIO_BARRIER();ready[half]=0;tx15_audio_report.dma_irqs++;
    if(!filled && remaining)tx15_audio_report.underruns++;
    if(filled)tx15_audio_report.frames+=TX15_AUDIO_HALF_FRAMES;
}
void tx15_audio_transport_stop(void) {
    if(!owned)return;
    W(0xe000e180u,1u<<15);running=0;
    if(configured) {
        W(SPI+8,0);W(SPI,0);modify(DMA,1,0);
        unsigned budget=1000;while((R(DMA)&1) && --budget) { }
        if(R(DMA)&1)return; /* Retain ownership/clocks if the DMA did not stop. */
        W(0x4002000cu,0x3d);W(0xe000e280u,1u<<15);
        modify(RCC+0xe8,1u<<14,0);
    }
    modify(RCC,1u<<26,0);configured=owned=0;ready[0]=ready[1]=remaining=0;
}
