/* New Deviation hardware bring-up; GPL-3.0-or-later. */
#include "../ram_probe/probe.h"
#include "../board/display.h"
#ifdef TX15_INPUT_DEMO
#include "../board/inputs.h"
#endif
#include "../board/power.h"
#include "../board/clock.h"

#define REG32(addr) (*(volatile uint32_t *)(addr))
#define SYST_CSR REG32(0xe000e010u)
#define SYST_RVR REG32(0xe000e014u)
#define SYST_CVR REG32(0xe000e018u)

volatile struct probe_report probe_report __attribute__((section(".mailbox"), aligned(8)));

_Static_assert(sizeof(struct probe_report) == 128, "mailbox ABI must match host decoder");

static void stop(void) __attribute__((noreturn));
static void stop(void)
{
    __asm volatile("cpsid i" ::: "memory");
    SYST_CSR = 0;
    for (;;) __asm volatile("nop");
}

void Probe_Fault(void)
{
    uint32_t exception;
    __asm volatile("mrs %0, ipsr" : "=r"(exception));
    probe_report.fault_exception = exception;
    probe_report.cfsr = REG32(0xe000ed28u);
    probe_report.hfsr = REG32(0xe000ed2cu);
    probe_report.mmfar = REG32(0xe000ed34u);
    probe_report.bfar = REG32(0xe000ed38u);
    probe_report.state = PROBE_FAULT;
    __asm volatile("dsb" ::: "memory");
    stop();
}

void SysTick_Handler(void)
{
    probe_report.ticks++;
#ifdef TX15_INPUT_DEMO
    tx15_inputs_tick();
#endif
}

/* Compact, purpose-built 5x7 glyphs for this bench image. */
static const char glyph_chars[]="NEW DEVIATION0123456789MRX";
static const uint8_t glyphs[][5]={
 {127,2,4,8,127},{127,73,73,73,65},{127,32,24,32,127},{0,0,0,0,0},
 {127,65,65,34,28},{127,73,73,73,65},{31,32,64,32,31},
 {0,65,127,65,0},{126,9,9,9,126},{1,1,127,1,1},{0,65,127,65,0},
 {62,65,65,65,62},{127,2,4,8,127},
 {62,81,73,69,62},{0,66,127,64,0},{66,97,81,73,70},{33,65,69,75,49},
 {24,20,18,127,16},{39,69,69,69,57},{60,74,73,73,48},
 {1,113,9,5,3},{54,73,73,73,54},{6,73,73,41,30},{127,2,12,2,127},{127,9,25,41,70},{99,20,8,20,99}};
static void rect(unsigned x,unsigned y,unsigned w,unsigned h,uint16_t c) {
    for(unsigned j=0;j<h;j++) for(unsigned i=0;i<w;i++) tx15_display_pixel(x+i,y+j,c);
}
static void letter(unsigned x,unsigned y,char ch,unsigned scale,uint16_t c) {
    unsigned k=0; while(glyph_chars[k] && glyph_chars[k]!=ch) k++;
    if(!glyph_chars[k]) return;
    for(unsigned i=0;i<5;i++) for(unsigned j=0;j<7;j++)
        if(glyphs[k][i]&(1u<<j)) rect(x+i*scale,y+j*scale,scale,scale,c);
}
static void draw_number(unsigned value) {
    rect(144,180,192,56,0x0841);
    for(unsigned n=0;n<4;n++) {
        letter(288-n*48,180,'0'+value%10,8,0xffff); value/=10;
    }
}
static void draw_screen(void) {
    tx15_display_fill(0x0841);
    rect(0,0,480,3,0xffff); rect(0,317,480,3,0xffff);
    rect(0,0,3,320,0xffff); rect(477,0,3,320,0xffff);
    const char title[]="NEW DEVIATION";
    for(unsigned i=0;i<sizeof(title)-1;i++) letter(45+i*30,40,title[i],5,0xffff);
    rect(30,110,140,40,0xf800); rect(170,110,140,40,0x07e0); rect(310,110,140,40,0x001f);
    /* Asymmetric corner markers expose rotation/mirroring. */
    rect(8,8,16,16,0xf800); rect(456,288,16,24,0x001f);
    draw_number(0);
}

#ifdef TX15_INPUT_DEMO
static unsigned selected, inside;
static void text(unsigned x,unsigned y,const char *s,unsigned scale,uint16_t color) {
    while(*s) { letter(x,y,*s++,scale,color); x+=6*scale; }
}
static void draw_menu(void) {
    rect(6,90,468,220,0x0841);
    if(inside) {
        text(70,135,"ENTER",5,0x07e0); letter(270,135,'1'+selected,5,0xffff);
        text(150,220,"EXIT",4,0xffff);
    } else for(unsigned i=0;i<3;i++) {
        unsigned y=96+i*55; uint16_t color=(i==selected)?0xffe0:0x4208;
        rect(45,y,390,44,color); text(110,y+7,"ITEM",4,0);
        letter(300,y+7,'1'+i,4,0);
    }
}
static void input_update(void) {
    struct tx15_input_event e=tx15_inputs_take();
    if(!e.pressed && !e.rotation) return;
    if(e.pressed&TX15_EXIT) inside=0;
    else if(!inside) {
        int delta=e.rotation;
        if(e.pressed&TX15_PREV) delta--;
        if(e.pressed&TX15_NEXT) delta++;
        int next=(int)selected+delta; if(next<0) next=0; if(next>2) next=2;
        selected=(unsigned)next;
        if(e.pressed&TX15_ENTER) inside=1;
    }
    draw_menu();
}
#endif

void Probe_Main(void)
{
    /* Startup initialized mailbox ECC with aligned doubleword stores. */
    probe_report.version = 6;
    probe_report.state = PROBE_INIT;
    probe_report.magic = PROBE_MAGIC;
    probe_report.cpuid = REG32(0xe000ed00u);
    probe_report.device_id = REG32(0x5c001000u);
    probe_report.rcc_cr = REG32(0x58024400u);
    probe_report.rcc_cfgr = REG32(0x58024410u);
    probe_report.rcc_d1cfgr = REG32(0x58024418u);
    probe_report.scb_ccr = REG32(0xe000ed14u);
    probe_report.mpu_ctrl = REG32(0xe000ed94u);
    probe_report.error = probe_environment_error(&probe_report);
    if (probe_report.error) {
        probe_report.state = PROBE_ERROR;
        stop();
    }

    tx15_power_init();
    probe_report.power_status = tx15_power_status();
    if ((probe_report.power_status & TX15_POWER_READY) != TX15_POWER_READY) {
        probe_report.error = BAD_POWER;
        probe_report.state = PROBE_ERROR;
        stop();
    }

    enum tx15_clock_result clock_result = tx15_clock_hse_init(1000000u);
    if (clock_result == TX15_CLOCK_OK)
        clock_result = tx15_clock_pll128_init(1000000u);
    probe_report.rcc_cr = REG32(0x58024400u);
    probe_report.rcc_cfgr = REG32(0x58024410u);
    probe_report.rcc_d1cfgr = REG32(0x58024418u);
    if (clock_result != TX15_CLOCK_OK) {
        probe_report.error = BAD_CLOCK;
        probe_report.state = PROBE_ERROR;
        stop();
    }

    if (tx15_sdram_init(&probe_report.sdram)) {
        probe_report.error = BAD_SDRAM; probe_report.state = PROBE_ERROR; stop();
    }
    /* Check only the framebuffer we actually use, including address aliasing. */
    volatile uint32_t *fb=(volatile uint32_t *)TX15_LCD_FB;
    for(unsigned i=0;i<TX15_LCD_BYTES/4;i++) fb[i]=0xa5a50000u^i;
    __asm volatile("dsb" ::: "memory");
    for(unsigned i=0;i<TX15_LCD_BYTES/4;i++) {
        if(fb[i]!=(0xa5a50000u^i)) {
            probe_report.sdram.bad_address=TX15_LCD_FB+i*4;
            probe_report.sdram.expected=0xa5a50000u^i; probe_report.sdram.actual=fb[i];
            probe_report.error=BAD_SDRAM; probe_report.state=PROBE_ERROR; stop();
        }
        probe_report.sdram.checks++;
    }
    probe_report.ram_words=probe_report.sdram.words=TX15_LCD_BYTES/4;
    probe_report.sdram.state=3;
    draw_screen();
    unsigned display_error=tx15_display_init();
    if(display_error) {
        probe_report.error=128u | (display_error<<8); probe_report.state=PROBE_ERROR; stop();
    }
    probe_report.rcc_cr=REG32(0x58024400u);
#ifdef TX15_INPUT_DEMO
    tx15_inputs_init(); draw_menu();
#endif
    /* Confirmed PLL128 processor clock, nominal 1 ms. */
    SYST_CSR = 0;
    SYST_RVR = TX15_PLL_CORE_HZ / 1000u - 1u;
    SYST_CVR = 0;
    REG32(0xe000ed04u) = (1u << 25) | (1u << 27); /* clear pending SysTick/PendSV */
    probe_report.state = PROBE_RUNNING;
    SYST_CSR = 7;
    __asm volatile("dsb\nisb\ncpsie i" ::: "memory");
    unsigned last=0;
    for (;;) {
        unsigned seconds=probe_report.ticks/1000;
#ifdef TX15_INPUT_DEMO
        input_update();
        if(seconds!=last) {
            last=seconds; probe_report.loops++;
            rect(360,280,90,24,0x0841);
            letter(360,280,'0'+(seconds/10)%10,3,0xffff);
            letter(384,280,'0'+seconds%10,3,0xffff);
        }
#else
        if(seconds!=last) { last=seconds; draw_number(seconds); probe_report.loops++; }
#endif
        probe_report.power_status = tx15_power_status();
    }
}
