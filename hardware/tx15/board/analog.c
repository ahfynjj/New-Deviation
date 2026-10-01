/* TX15 ADC1 polling backend. GPL-3.0-or-later.
 * Register definitions checked against ST stm32h750xx.h / stm32h7xx_ll_adc.h.
 * Requires the established HCLK=64MHz bootstrap, ADC12 reset-idle.
 * No DMA, IRQ, external module power or Flash access.
 */
#include "analog.h"
#define R(a) (*(volatile uint32_t *)(a))
#define ADC 0x40022000u
#define RCC 0x58024400u
#define CR R(ADC+8)
static const unsigned channels[6]={3,13,4,8,11,5};
volatile uint16_t tx15_analog_raw[6];
volatile uint32_t tx15_analog_status, tx15_analog_frames;
static int wait_mask(uint32_t address,uint32_t mask,uint32_t expected) {
    for(unsigned n=0;n<2000000;n++) if((R(address)&mask)==expected) return 0;
    return -1;
}
static void pin(unsigned port,unsigned n) {
    uint32_t b=0x58020000u+port*0x400u;
    R(b)|=3u<<(2*n); R(b+12)&=~(3u<<(2*n));
}
int tx15_analog_init(void) {
    tx15_analog_status=1;
    if((R(RCC+0xd8)&32) || (R(RCC+0x80)&32)
       || (R(RCC+0x18)&0xf7f)!=0x48
       || (R(0x5c001000u)&0x30000000u)!=0x20000000u) return -1;
    R(RCC+0xe0)|=7; (void)R(RCC+0xe0);
    pin(0,6); pin(2,3); pin(2,4); pin(2,5); pin(2,1); pin(1,1);
    R(RCC+0xd8)|=32; (void)R(RCC+0xd8);
    R(ADC+0x308)=3u<<16; /* synchronous HCLK/4 = 16MHz */
    CR=(1u<<28)|(2u<<8); /* regulator enabled, deep power down off, boost */
    for(volatile unsigned n=0;n<12800;n++) __asm volatile("nop");
    CR|=(1u<<16)|(1u<<31); /* single-ended offset + linearity calibration */
    if(wait_mask(ADC+8,1u<<31,0)) { tx15_analog_status=2; return -1; }
    R(ADC+0xc)=2u<<2; /* 12 bit, software trigger, single conversion */
    R(ADC+0x10)=0; R(ADC+0xc0)=0;
    uint32_t selected=0;
    for(unsigned i=0;i<6;i++) {
        unsigned ch=channels[i]; selected|=1u<<ch;
        uint32_t addr=ADC+(ch<10?0x14:0x18),shift=(ch%10)*3;
        R(addr)=(R(addr)&~(7u<<shift))|(5u<<shift); /* 64.5 cycles */
    }
    R(ADC+0x1c)=selected;
    R(ADC)=1; CR|=1;
    if(wait_mask(ADC,1,1)) { tx15_analog_status=3; return -1; }
    tx15_analog_status=4;
    return tx15_analog_sample();
}
int tx15_analog_sample(void) {
    if(tx15_analog_status!=4) return -1;
    uint16_t values[6];
    for(unsigned i=0;i<6;i++) {
        if(wait_mask(ADC+8,4,0)) { tx15_analog_status=5; return -1; }
        R(ADC+0x30)=channels[i]<<6;
        R(ADC)=0x1c; CR|=4;
        if(wait_mask(ADC,4,4)) { tx15_analog_status=6; return -1; }
        values[i]=(uint16_t)(R(ADC+0x40)&4095);
    }
    for(unsigned i=0;i<6;i++) tx15_analog_raw[i]=values[i];
    tx15_analog_frames++;
    return 0;
}
