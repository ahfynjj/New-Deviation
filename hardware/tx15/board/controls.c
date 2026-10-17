/* Native TX15 I2C4 input reader; GPL-3.0-or-later.
 * PD12/PD13 AF4, expander reset PG10; 7-bit 0x74/0x75.
 * Register facts: ST stm32h750xx.h; fixed TX15 board pin definitions.
 * Called from the main loop only. No I2C operation in SysTick/interrupts.
 * Only expander input registers are read; RF and touch are not configured.
 */
#include "controls.h"
#ifndef TX15_READ32
#define TX15_READ32(a) (*(volatile uint32_t *)(a))
#define TX15_WRITE32(a,v) (*(volatile uint32_t *)(a)=(v))
#endif
#define I2C 0x58001c00u
#define RCC 0x58024400u
struct tx15_controls tx15_controls;
volatile uint32_t tx15_controls_status,tx15_controls_frames,tx15_controls_errors;
volatile uint16_t tx15_controls_raw[2];
static unsigned sampled,locked;
static uint32_t audio_status;
uint32_t tx15_controls_audio_status(void) {return audio_status;}
static unsigned msec(void) {return TX15_READ32(0x2400e02cu);}
static void modify(uint32_t a,uint32_t mask,uint32_t value) {
    TX15_WRITE32(a,(TX15_READ32(a)&~mask)|value);
}
static int wait_bounded(uint32_t mask,uint32_t expected,unsigned start,unsigned timeout) {
    for(unsigned n=0;n<20000;n++) {
        uint32_t status=TX15_READ32(I2C+0x18);
        if(status&0x3710u) return -1; /* NACK/BERR/ARLO/OVR/timeout/alert. */
        if((status&mask)==expected) return 0;
        if((unsigned)(msec()-start)>=timeout) break;
    }
    return -1;
}
static int wait_status(uint32_t mask,uint32_t expected,unsigned start) {
    return wait_bounded(mask,expected,start,3);
}
#ifndef TX15_AUDIO_CYCLES
#define TX15_AUDIO_CYCLES() TX15_READ32(0xe0001004u)
static int audio_clock_start(void) {
    /* Do not reset CYCCNT: another diagnostic may already be using it. */
    modify(0xe000edfcu,0,1u<<24);
    /* Cortex-M7 DWT can be locked after cold boot without a debugger. */
    if((TX15_READ32(0xe0001fb4u)&3u)==3u)TX15_WRITE32(0xe0001fb0u,0xc5acce55u);
    if(TX15_READ32(0xe0001000u)&(1u<<25))return -1;
    modify(0xe0001000u,0,1);
    return (TX15_READ32(0xe0001000u)&1)?0:-1;
}
#else
static int audio_clock_start(void) {return 0;}
#endif
static int wait_audio(uint32_t mask,uint32_t expected,uint32_t start) {
    for(unsigned n=0;n<20000;n++) {
        uint32_t status=TX15_READ32(I2C+0x18);
        if(status&0x3710u)return -1;
        if((status&mask)==expected)return 0;
        if((uint32_t)(TX15_AUDIO_CYCLES()-start)>=128000u)break;
    }
    return -1;
}
static int read_port(unsigned address,uint16_t *value) {
    if(locked)return -1;
    locked=1;
    unsigned start=msec();
    uint32_t base=address<<1;
    if(wait_status(1u<<15,0,start)) goto failed;
    TX15_WRITE32(I2C+0x1c,0x3f38); /* Clear old transfer flags. */
    TX15_WRITE32(I2C+4,base|(1u<<16)|(1u<<13));
    if(wait_status(2,2,start)) goto failed;
    TX15_WRITE32(I2C+0x28,0); /* INPUT0 register pointer; no output/config write. */
    if(wait_status(64,64,start)) goto failed;
    TX15_WRITE32(I2C+4,base|(1u<<10)|(2u<<16)|(1u<<25)|(1u<<13));
    if(wait_status(4,4,start)) goto failed;
    unsigned lo=TX15_READ32(I2C+0x24)&255;
    if(wait_status(4,4,start)) goto failed;
    unsigned hi=TX15_READ32(I2C+0x24)&255;
    if(wait_status(32,32,start)) goto failed;
    TX15_WRITE32(I2C+0x1c,32);
    *value=(uint16_t)(lo|(hi<<8));locked=0; return 0;
failed:
    modify(I2C+4,0,1u<<14); /* Request STOP, do not wait without a deadline. */
    TX15_WRITE32(I2C,0); TX15_WRITE32(I2C+0x1c,0x3f38);
    locked=0;
    return -1;
}
static int audio_transfer(unsigned reg,unsigned *value,int read) {
    audio_status=0xffffffffu; /* Not admitted: no audio transaction snapshot. */
    if(locked || tx15_controls_status!=1 || reg>127 || !(TX15_READ32(I2C)&1))return -1;
    if(audio_clock_start()) {audio_status=0xfffffffeu;return -1;}
    audio_status=TX15_READ32(I2C+0x18);
    locked=1;uint32_t start=TX15_AUDIO_CYCLES(),base=0x18u<<1;
    if(wait_audio(1u<<15,0,start))goto failed_audio;
    TX15_WRITE32(I2C+0x1c,0x3f38);
    TX15_WRITE32(I2C+4,base|((read?1u:2u)<<16)|(read?0:1u<<25)|(1u<<13));
    if(wait_audio(2,2,start))goto failed_audio;
    TX15_WRITE32(I2C+0x28,reg);
    if(read) {
        if(wait_audio(64,64,start))goto failed_audio;
        TX15_WRITE32(I2C+4,base|(1u<<10)|(1u<<16)|(1u<<25)|(1u<<13));
        if(wait_audio(4,4,start))goto failed_audio;
        *value=TX15_READ32(I2C+0x24)&255;
    } else {
        if(wait_audio(2,2,start))goto failed_audio;
        TX15_WRITE32(I2C+0x28,*value);
    }
    if(wait_audio(32,32,start))goto failed_audio;
    audio_status=TX15_READ32(I2C+0x18);
    TX15_WRITE32(I2C+0x1c,32);locked=0;return 0;
failed_audio:
    audio_status=TX15_READ32(I2C+0x18);
    modify(I2C+4,0,1u<<14);
    TX15_WRITE32(I2C+0x1c,0x3f38);locked=0;return -1;
}
int tx15_controls_audio_write(unsigned reg,unsigned value) {
    if(value>255)return -1;
    return audio_transfer(reg,&value,0);
}
int tx15_controls_audio_read(unsigned reg,uint8_t *value) {
    unsigned result;if(!value || audio_transfer(reg,&result,1))return -1;
    *value=(uint8_t)result;return 0;
}
static int bus_init(void) {
    /* Select undivided HSI64 as I2C4 kernel clock independently of APB4. */
    if((TX15_READ32(RCC)&0x1cu)!=4) return -1;
    modify(RCC+0xe0,0,(1u<<3)|(1u<<6)); (void)TX15_READ32(RCC+0xe0);
    const uint32_t d=0x58020c00u,g=0x58021800u;
    TX15_WRITE32(g+0x18,1u<<26); /* Expander reset low before enabling output. */
    modify(g,3u<<20,1u<<20); modify(g+4,1u<<10,0);
    for(volatile unsigned n=0;n<128;n++) { }
    TX15_WRITE32(g+0x18,1u<<10);
    for(unsigned pin=12;pin<=13;pin++) {
        unsigned shift=pin*2,af=(pin-8)*4;
        modify(d,3u<<shift,2u<<shift);
        modify(d+4,0,1u<<pin); /* Open drain. */
        modify(d+8,3u<<shift,1u<<shift);
        modify(d+12,3u<<shift,1u<<shift);
        modify(d+0x24,15u<<af,4u<<af);
    }
    modify(RCC+0x58,3u<<8,2u<<8);
    modify(RCC+0xf4,0,1u<<7); (void)TX15_READ32(RCC+0xf4);
    modify(RCC+0x9c,0,1u<<7); modify(RCC+0x9c,1u<<7,0);
    TX15_WRITE32(I2C,0);
    /* HSI64, PRESC=7 (125ns), SCLDEL=12, SDADEL=2, SCLH=35, SCLL=43.
     * Standard-mode about 98kHz including the enabled analog filter. */
    TX15_WRITE32(I2C+0x10,0x70c2232bu);
    TX15_WRITE32(I2C+0x1c,0x3f38); TX15_WRITE32(I2C,1);
    return 0;
}
static int sample(unsigned now) {
    uint16_t a,b;
    if(read_port(0x74,&a) || read_port(0x75,&b)) {
        tx15_controls_errors++;tx15_controls_status=2;
        tx15_controls_invalidate(&tx15_controls);return -1;
    }
    tx15_controls_raw[0]=a;tx15_controls_raw[1]=b;
    tx15_controls_decode(&tx15_controls,a,b,now);
    tx15_controls_frames++;tx15_controls_status=1;return 0;
}
int tx15_controls_init(void) {
    tx15_controls_reset(&tx15_controls);sampled=msec();
    if(bus_init()) {tx15_controls_status=3;return -1;}
    return sample(sampled);
}
void tx15_controls_poll(unsigned now) {
    unsigned interval=tx15_controls_status==1?10:1000;
    if((unsigned)(now-sampled)<interval) return;
    sampled=now;
    if(tx15_controls_status!=1 && bus_init()) {tx15_controls_status=3;return;}
    (void)sample(now);
}
