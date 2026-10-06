/* TX15 ADC3 PH3/channel14 battery input; GPL-3.0-or-later. */
#include "battery.h"
#include "status.h"
#define R(a) (*(volatile uint32_t *)(a))
#define ADC 0x58026000u
#define RCC 0x58024400u
volatile uint32_t tx15_battery_status,tx15_battery_mv,tx15_battery_raw;
static int wait(uint32_t a,uint32_t mask,uint32_t value) {
 for(unsigned n=0;n<200000;n++)if((R(a)&mask)==value)return 1;return 0;
}
void tx15_battery_init(void) {
 tx15_battery_status=1;
 if((R(RCC+0x88)&(1u<<24)) || (R(RCC+0xe0)&(1u<<24)))return;
 R(RCC+0xe0)|=(1u<<7)|(1u<<24);(void)R(RCC+0xe0);
 R(0x58021c00u)|=3u<<6;R(0x58021c0cu)&=~(3u<<6);
 R(ADC+0x308)=3u<<16; /* synchronous HCLK/4 */
 R(ADC+8)=(1u<<28)|(2u<<8);
 for(volatile unsigned n=0;n<12800;n++)__asm volatile("nop");
 R(ADC+8)|=(1u<<16)|(1u<<31);
 if(!wait(ADC+8,1u<<31,0))return;
 R(ADC+0xc)=2u<<2;R(ADC+0x10)=0;R(ADC+0xc0)=0;
 R(ADC+0x18)=7u<<12; /* long sampling, high impedance divider */
 R(ADC+0x1c)=1u<<14;R(ADC+0x30)=14u<<6;
 R(ADC)=1;R(ADC+8)|=1;
 if(!wait(ADC,1,1))return;tx15_battery_status=2;
}
void tx15_battery_poll(uint32_t now) {
 static uint32_t previous; if(now-previous<100 || tx15_battery_status!=2)return;previous=now;
 if(!wait(ADC+8,4,0)){tx15_battery_mv=0;tx15_battery_status=3;return;}
 R(ADC)=0x1c;R(ADC+8)|=4;
 if(!wait(ADC,4,4)){tx15_battery_mv=0;tx15_battery_status=3;return;}
 unsigned raw=R(ADC+0x40)&4095;tx15_battery_raw=raw;
 unsigned mv=tx15_battery_scale(raw);
 tx15_battery_mv=tx15_battery_mv ? (tx15_battery_mv*7+mv+4)/8 : mv;
}
