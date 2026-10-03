#include <assert.h>
#include "hardware/tx15/boot/handoff.h"
#include "hardware/tx15/boot/power_button.h"
int main(void) {
    struct probe_report r={0};r.magic=PROBE_MAGIC;r.version=9;r.state=3;
    r.cpuid=0x411fc271;r.device_id=0x20036450;r.rcc_cr=0x33030005;r.rcc_cfgr=0x1b;r.rcc_d1cfgr=0x48;
    r.power_status=15;r.ram_words=TX15_BOOT_READY;r.sdram.state=2;
    assert(tx15_boot_handoff_valid(&r));
    uint32_t *words=(uint32_t *)&r;
    for(unsigned i=0;i<32;i++) {
        uint32_t saved=words[i];
        if(i==0 || i==1 || i==2 || i==4 || i==5 || i==6 || i==7 || i==8 || i==13 || i==19 || i==20) {
            words[i]=0;assert(!tx15_boot_handoff_valid(&r));words[i]=saved;
        }
        if(i==3 || i==10 || (i>=14 && i<=18) || i==21) {
            words[i]=1;assert(!tx15_boot_handoff_valid(&r));words[i]=saved;
        }
    }
    r.scb_ccr=0x10000;assert(!tx15_boot_handoff_valid(&r));
    r.scb_ccr=0;r.version=6;assert(!tx15_boot_handoff_valid(&r));
    struct tx15_power_button b={0};
    assert(!tx15_power_button_poll(&b,0,1));assert(!tx15_power_button_poll(&b,10000,1));
    assert(!tx15_power_button_poll(&b,10010,0));assert(!tx15_power_button_poll(&b,10015,1));
    assert(!tx15_power_button_poll(&b,10020,0));assert(!tx15_power_button_poll(&b,10040,0));
    assert(!tx15_power_button_poll(&b,10100,1));assert(!tx15_power_button_poll(&b,12099,1));
    assert(tx15_power_button_poll(&b,12100,1));assert(tx15_power_button_poll(&b,12101,0));
    b=(struct tx15_power_button){0};
    assert(!tx15_power_button_poll(&b,0xffffff00,0));assert(!tx15_power_button_poll(&b,0xffffff20,0));
    assert(!tx15_power_button_poll(&b,0xffffff30,1));assert(!tx15_power_button_poll(&b,0xffffff40,0));
    assert(!tx15_power_button_poll(&b,0xffffff50,1));assert(!tx15_power_button_poll(&b,0x710,1));
    assert(tx15_power_button_poll(&b,0x720,1));
    return 0;
}
