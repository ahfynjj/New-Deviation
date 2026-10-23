/* New Deviation TX15; GPL-3.0-or-later.
 * Panel command values/pins/timings reference EdgeTX rm-h750 lcd_driver_480.cpp
 * (GPL-2.0-only), commit 19b50d967e6e579ac5a1b3bdb014b148a6b47491.
 * Independent bare-metal driver; no EdgeTX application/runtime dependency.
 */
#include "display.h"
#ifdef TX15_BUFFERED_DISPLAY
#include "display_buffer.h"
#endif
#ifndef TX15_DISPLAY_REGISTER
#define TX15_DISPLAY_REGISTER(a) (*(volatile uint32_t *)(a))
#endif
#ifndef TX15_DISPLAY_BARRIER
#define TX15_DISPLAY_BARRIER() __asm volatile("dsb" ::: "memory")
#endif
#define R(a) TX15_DISPLAY_REGISTER(a)
#define RCC 0x58024400u
#define LTDC 0x50001000u
#define GPIO(p) (0x58020000u + (p)*0x400u)
static void modify(uint32_t a,uint32_t mask,uint32_t v) { R(a)=(R(a)&~mask)|v; }
static void delay(unsigned n) { for(volatile unsigned i=0;i<n;i++) __asm volatile("nop"); }
static int delay_clock_start(void) {
    /* Fixed core128 profile checked by init. Unlock cold M7 DWT, preserve
     * CYCCNT and other users' settings. No timer IRQ or SysTick ownership. */
    R(0xe000edfcu)|=1u<<24;
    if((R(0xe0001fb4u)&3u)==3u)R(0xe0001fb0u)=0xc5acce55u;
    if(R(0xe0001000u)&(1u<<25))return 0;
    R(0xe0001000u)|=1u;
    uint32_t start=R(0xe0001004u);
    for(unsigned budget=10000;budget;budget--)
        if(R(0xe0001004u)!=start)return 1;
    return 0;
}
static int ms(unsigned n) {
    while(n--) {
        uint32_t start=R(0xe0001004u);unsigned budget=128000;
        while((uint32_t)(R(0xe0001004u)-start)<128000u)
            if(!--budget)return 0;
    }
    return 1;
}
static void output(unsigned p,unsigned pin,unsigned high) { R(GPIO(p)+24)=1u<<(pin+(high?0:16)); }
static void mode(unsigned p,unsigned pin,unsigned af) {
    uint32_t b=GPIO(p),s=pin*2u;
    modify(b+4,1u<<pin,0); modify(b+8,3u<<s,0); modify(b+12,3u<<s,0);
    if(af) modify(b+32+(pin/8)*4,15u<<((pin%8)*4),af<<((pin%8)*4));
    modify(b,3u<<s,(af?2u:1u)<<s);
}
static void serial(unsigned data,unsigned value) {
    unsigned bits=(data<<8)|value;
    for(unsigned n=0;n<9;n++) {
        output(1,0,0); delay(64); output(8,9,(bits&0x100u)!=0);
        delay(64); output(1,0,1); delay(64); bits<<=1;
    }
    output(1,0,0);
}
static void command(unsigned c) { serial(0,c); }
static void parameter(unsigned v) { serial(1,v); }
static void unlock(void) { command(0xf0); parameter(0xc3); command(0xf0); parameter(0x96); }
int tx15_display_init(void) {
    if ((R(RCC)&0x3f0f001du)!=0x03030005u || (R(RCC+16)&0x3fu)!=0x1bu
        || (R(RCC+0x18)&0xf7fu)!=0x48u || (R(RCC+0xe4)&8u)
        || (R(0xe000ed14u)&0x30000u) || (R(0xe000ed94u)&1u)) return 1;
    if(!delay_clock_start())return 3;
    /* HSE48 / M12 * N64 / R24 = 10.666667MHz; wide VCO256MHz. */
    modify(RCC+0x28,0x03f00000u,12u<<20);
    modify(RCC+0x2c,0x01c00f00u,0x01000800u);
    R(RCC+0x40)=0x1701023fu;
    modify(RCC,1u<<28,1u<<28);
    unsigned budget=1000000;
    while(!(R(RCC)&(1u<<29))) if(!--budget) return 2;
    modify(RCC+0xe0,0x703u,0x703u); (void)R(RCC+0xe0);
    output(0,10,0); mode(0,10,0); /* backlight off during initialization */
    output(0,7,1); mode(0,7,0); output(1,0,0); mode(1,0,0);
    output(8,9,0); mode(8,9,0); output(9,12,1); mode(9,12,0);
    if(!ms(1))return 3;
    output(9,12,0);if(!ms(10))return 3;
    output(9,12,1);if(!ms(100))return 3;
    const uint16_t pins[]={0x7000,0xce7e,0x00ff};
    for(unsigned p=0;p<3;p++) for(unsigned pin=0;pin<16;pin++)
        if(pins[p]&(1u<<pin)) mode(p+8,pin,14);
    output(0,7,0);if(!ms(1))return 3;
    command(0x11);if(!ms(120))return 3;unlock();
    command(0x11);if(!ms(120))return 3;unlock();
    /* Length, command, parameters; the panel consumes RGB666 on its RGB bus. */
    static const uint8_t seq[]={
        1,0x36,0xe8, 4,0x2a,0,0,1,0xdf, 4,0x2b,0,0,1,0x3f,
        1,0x3a,0x66, 1,0xb4,1, 3,0xb6,0x20,2,0x3b, 1,0xb7,0xc6,
        2,0xc0,0x80,0x45, 1,0xc1,0x0f, 1,0xc2,0xa7, 1,0xc5,0x0a,
        8,0xe8,0x40,0x8a,0,0,0x29,0x19,0xa5,0x33,
        14,0xe0,0xd0,8,0x0f,6,6,0x33,0x30,0x33,0x47,0x17,0x13,0x13,0x2b,0x31,
        14,0xe1,0xd0,0x0a,0x11,0x0b,9,7,0x2f,0x33,0x47,0x38,0x15,0x16,0x2c,0x32,
        1,0xf0,0x3c, 1,0xf0,0x69
    };
    for(unsigned i=0;i<sizeof(seq);) {
        unsigned n=seq[i++]; command(seq[i++]); while(n--) parameter(seq[i++]);
    }
    if(!ms(120))return 3;
    command(0x21);output(0,7,1);if(!ms(1))return 3;
    modify(RCC+0xe4,8,8); (void)R(RCC+0xe4);
    modify(RCC+0x8c,8,8); modify(RCC+0x8c,8,0);
    R(LTDC+8)=0x00050001; R(LTDC+12)=0x0019000b;
    R(LTDC+16)=0x015901eb; R(LTDC+20)=0x018101f5;
    R(LTDC+0x2c)=0; R(LTDC+0x34)=0; /* black background, IRQs off */
    R(LTDC+0x88)=0x0159001a; R(LTDC+0x8c)=0x01eb000c;
    R(LTDC+0x94)=2; R(LTDC+0x98)=255; R(LTDC+0x9c)=0;
    R(LTDC+0xa0)=0x405; R(LTDC+0xac)=TX15_LCD_FB;
    R(LTDC+0xb0)=(640u<<16)|647u; R(LTDC+0xb4)=480;
    R(LTDC+0x84)=1; R(LTDC+0x104)=0; /* layer2 off */
    R(LTDC+0x18)=0x10012221; R(LTDC+0x24)=1;
    TX15_DISPLAY_BARRIER();
    output(0,7,0);if(!ms(1))return 3;
    command(0x29);output(0,7,1);
    output(0,10,1);
    return 0;
}
void tx15_display_pixel(unsigned x,unsigned y,uint16_t color) {
#ifdef TX15_BUFFERED_DISPLAY
    tx15_display_buffer_pixel(x,y,color);
#else
    if(x<TX15_LCD_WIDTH && y<TX15_LCD_HEIGHT)
        ((volatile uint16_t *)TX15_LCD_FB)[tx15_display_offset(x,y)]=color;
#endif
}
void tx15_display_fill(uint16_t color) {
#ifdef TX15_BUFFERED_DISPLAY
    tx15_display_buffer_rect(0,0,TX15_LCD_WIDTH,TX15_LCD_HEIGHT,color);
#else
    for(unsigned i=0;i<TX15_LCD_BYTES/2;i++) ((volatile uint16_t *)TX15_LCD_FB)[i]=color;
    TX15_DISPLAY_BARRIER();
#endif
}
