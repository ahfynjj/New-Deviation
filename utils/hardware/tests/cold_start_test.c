#include <assert.h>
#include <stdint.h>
static uint32_t cr,cfgr,d1,d2,d3,sel,cfg,div,supply,vos,actual,flash;
static unsigned writes,reads;
static int fail_supply,fail_voltage,fail_flash,fail_hse,fail_pll;
static uint32_t rd(uint32_t a) {
    assert(++reads<1000);
    switch(a) {
    case 0x58024400:
        if ((cr&0x10000) && !fail_hse) cr|=0x20000;
        if ((cr&0x1000000) && !fail_pll) cr|=0x2000000;
        return cr;
    case 0x58024410: return cfgr;
    case 0x58024418: return d1;
    case 0x5802441c: return d2;
    case 0x58024420: return d3;
    case 0x58024428: return sel;
    case 0x5802442c: return cfg;
    case 0x58024430: return div;
    case 0x5802480c: return supply;
    case 0x58024818: return vos;
    case 0x58024804: return actual;
    case 0x52002000: return flash;
    case 0xe000ed14: return 0; // reset cache off
    case 0xe000ed94: return 0;
    default: assert(0); return 0;
    }
}
static void wr(uint32_t a,uint32_t v) {
    writes++;
    switch(a) {
    case 0x5802480c:
        assert((v&7)==2 && (cr&0x3f0f0000)==0);
        supply=v; actual=fail_supply?0:0x6000; return;
    case 0x58024818:
        assert((supply&7)==2 && (actual&0x2000) && (cr&0x3f0f0000)==0);
        vos=(v&~0x2000u)|(fail_voltage?0:0x2000);
        actual=fail_voltage?0x6000:0xe000;return;
    case 0x52002000:
        assert((cr&0x3f0f0000)==0 && (vos&0xe000)==0xe000);
        if (!fail_flash) flash=v;
        return;
    case 0x58024400:
        assert((vos&0xe000)==0xe000 && (actual&0xe000)==0xe000 && (flash&15)>=2);
        cr=v;return;
    case 0x58024410:
        if ((v&7)==2) assert(cr&0x20000);
        if ((v&7)==3) assert((cr&0x3000000)==0x3000000 && d1==0x48 && d2==0x440 && d3==0x40);
        cfgr=(v&~0x38u)|((v&7)<<3);return;
    case 0x58024418: d1=v;return;
    case 0x5802441c: d2=v;return;
    case 0x58024420: d3=v;return;
    case 0x58024428: sel=v;return;
    case 0x5802442c: cfg=v;return;
    case 0x58024430: div=v;return;
    default: assert(0);
    }
}
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#include "hardware/tx15/board/clock.c"
#include "hardware/tx15/board/pll.c"
#include "hardware/tx15/boot/cold_start.c"
static void reset(void) {
    cr=0x4025;cfgr=d1=d2=d3=sel=cfg=div=0;
    supply=0x05000042;vos=0x4000;actual=0x6000;flash=0x30;
    reads=writes=0;fail_supply=fail_voltage=fail_flash=fail_hse=fail_pll=0;
}
int main(void) {
    reset();assert(tx15_boot_clock_init(8)==TX15_CLOCK_OK);
    assert((supply&7)==2 && (supply&~7u)==0x05000040 && (vos&0xe000)==0xe000);
    assert(flash==0x32 && cr==0x3034025 && cfgr==0x1b);
    reset();supply&=~4u;actual=0xe000;vos=0xe000;flash=0x35;
    assert(tx15_boot_clock_init(8)==TX15_CLOCK_OK);assert(flash==0x35);
    reset();supply|=4;assert(tx15_boot_clock_init(8)==TX15_CLOCK_BAD_STATE);assert(!writes);
    reset();actual=0;assert(tx15_boot_clock_init(8)==TX15_CLOCK_BAD_STATE);assert(!writes);
    reset();fail_voltage=1;assert(tx15_boot_clock_init(8)==TX15_CLOCK_VOLTAGE_TIMEOUT);assert(!(cr&0x10000));
    reset();fail_flash=1;assert(tx15_boot_clock_init(8)==TX15_CLOCK_FLASH_TIMEOUT);assert(!(cr&0x10000));
    reset();fail_hse=1;assert(tx15_boot_clock_init(8)==TX15_CLOCK_HSE_TIMEOUT);
    reset();fail_pll=1;assert(tx15_boot_clock_init(8)==TX15_CLOCK_PLL_TIMEOUT);
    for (unsigned i=0;i<7;i++) {
        reset();
        if(i==0)cr|=0x1000000;
        if(i==1)cfgr=0x1b;
        if(i==2)d2=0x440;
        if(i==3)supply=1;
        if(i==4)flash=15;
        if(i==5)cr|=8;
        if(i==6)d3=0x40;
        assert(tx15_boot_clock_init(8)==TX15_CLOCK_BAD_STATE);assert(!writes);
    }
    reset();assert(tx15_boot_clock_init(0)==TX15_CLOCK_BAD_STATE);assert(!writes);
}
