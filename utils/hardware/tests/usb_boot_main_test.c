#include <assert.h>
#include <setjmp.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
static uint32_t *reg(uint32_t);
static void assembly(void);
#define TX15_BOOT_REGISTER(a) (*reg(a))
#define TX15_BOOT_ASM(...) assembly()
#define TX15_USB_UPDATE 1
#include "../../../hardware/tx15/boot/main.c"
static uint32_t addresses[64],values[64];static unsigned used,scenario,init_calls,updates,jumps,loads;
static uint32_t update_id;
static jmp_buf exit_gate;
static uint32_t *reg(uint32_t address) {
    for(unsigned i=0;i<used;i++)if(addresses[i]==address)return values+i;
    assert(used<64);addresses[used]=address;values[used]=0;return values+used++;
}
static void assembly(void) { if(probe_report.state==PROBE_ERROR)longjmp(exit_gate,1); }
void tx15_power_init(void){}
uint32_t tx15_power_status(void){return 15;}
enum tx15_clock_result tx15_boot_clock_init(uint32_t budget){(void)budget;return TX15_CLOCK_OK;}
int tx15_sdram_init(volatile struct tx15_sdram_report *r){memset((void*)r,0,sizeof(*r));return 0;}
enum tx15_qspi_result tx15_boot_qspi_init(uint32_t *id,uint32_t budget){
    (void)budget;init_calls++;*id=scenario==2?0xef4018:0xc84018;
    return scenario==1 || (scenario==3 && init_calls==2)?TX15_QSPI_TIMEOUT:TX15_QSPI_OK;
}
void tx15_boot_qspi_stop(void){}
enum tx15_qspi_result tx15_boot_qspi_read(uint32_t o,uint8_t *d,uint32_t n,uint32_t b){
    (void)o;(void)d;(void)n;(void)b;return TX15_QSPI_OK;
}
enum tx15_boot_load_result tx15_boot_load(const struct tx15_boot_io *io,uint32_t o,uint32_t n,
    uint8_t *p,uint32_t cap,uint32_t *entry){
    (void)io;(void)o;(void)n;(void)p;(void)cap;loads++;*entry=0x24010001;
    return scenario==3?TX15_BOOT_LOAD_READ_ERROR:(scenario==5?TX15_BOOT_LOAD_BAD_IMAGE:TX15_BOOT_LOAD_OK);
}
unsigned tx15_boot_exit_stable(void){return scenario==4;}
int tx15_boot_update_mode(unsigned pressed,enum tx15_boot_load_result r){
    return (r==TX15_BOOT_LOAD_OK && pressed)||r==TX15_BOOT_LOAD_READ_ERROR||r==TX15_BOOT_LOAD_BAD_IMAGE;
}
void tx15_boot_update_run(uint32_t id){updates++;update_id=id;longjmp(exit_gate,2);}
void tx15_display_fill(uint16_t c){(void)c;}
int tx15_display_init(void){return 0;}
int tx15_boot_handoff_valid(const volatile struct probe_report *r){(void)r;return 1;}
void tx15_boot_jump(uint32_t entry){assert(entry==0x24010001);jumps++;longjmp(exit_gate,3);}
int main(void){
    for(scenario=1;scenario<=6;scenario++) {
        used=init_calls=updates=jumps=loads=0;update_id=0xffffffff;
        memset((void*)&probe_report,0,sizeof(probe_report));
        *reg(0xe000ed00)=0x411fc271;*reg(0x5c001000)=0x450;*reg(0x58024400)=5;
        if(!setjmp(exit_gate))Boot_Main();
        if(scenario<=3){assert(updates==1 && update_id==0 && probe_report.error && !jumps);}
        if(scenario==1||scenario==2)assert(loads==0);
        if(scenario==4||scenario==5)assert(updates==1 && update_id==0xc84018 && !jumps);
        if(scenario==6)assert(!updates && jumps==1 && loads==1);
    }
    puts("Boot_Main QSPI timeout/wrong ID/read-reinit failure, EXIT, bad image and normal routes passed");
    return 0;
}
