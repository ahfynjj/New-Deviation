#include <assert.h>
#include "src/target/tx/radiomaster/tx15/boot_contract.h"
int main(void) {
    struct probe_report r={0};r.magic=PROBE_MAGIC;r.state=3;
    r.cpuid=0x411fc271;r.device_id=0x20036450;r.rcc_cr=0x33030005;r.rcc_cfgr=0x1b;r.rcc_d1cfgr=0x48;
    r.power_status=15;r.ram_words=31;r.sdram.state=2;r.loops=99;
#ifdef TX15_STANDALONE
    r.version=6;assert(!tx15_app_boot_accept(&r));
    r.version=9;r.ram_words=7;assert(!tx15_app_boot_accept(&r));
    r.ram_words=31;assert(tx15_app_boot_accept(&r));assert(r.version==10);
#else
    r.version=9;assert(!tx15_app_boot_accept(&r));
    r.version=6;assert(tx15_app_boot_accept(&r));assert(r.version==7);
#endif
    assert(r.state==1 && !r.loops);assert(!tx15_app_boot_accept(&r));return 0;
}
