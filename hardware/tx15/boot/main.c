/* Native read-only cold loader; no Flash program/erase or original firmware. */
#include "cold_start.h"
#include "qspi.h"
#include "loader.h"
#include "../ram_probe/probe.h"
#include "../board/power.h"
#include "../board/display.h"
#include "handoff.h"
#ifdef TX15_RAM_CHAIN
#include "chain_source.h"
volatile struct tx15_chain_control chain_control __attribute__((aligned(8)));
#endif
#define R(a) (*(volatile uint32_t *)(a))
volatile struct probe_report probe_report __attribute__((section(".mailbox"),aligned(8)));
static void stop(void) __attribute__((noreturn));
static void stop(void) { __asm volatile("cpsid i");R(0xe000e010u)=0;for(;;)__asm volatile("nop"); }
void Boot_Fault(void) {
    uint32_t exception;__asm volatile("mrs %0,ipsr":"=r"(exception));
    probe_report.fault_exception=exception;probe_report.cfsr=R(0xe000ed28u);probe_report.hfsr=R(0xe000ed2cu);
    probe_report.mmfar=R(0xe000ed34u);probe_report.bfar=R(0xe000ed38u);probe_report.state=PROBE_FAULT;stop();
}
static void fail(uint32_t error) { probe_report.error=error;probe_report.state=PROBE_ERROR;stop(); }
static int read_image(void *ctx,uint32_t offset,uint8_t *dst,uint32_t bytes) {
    (void)ctx;
#ifdef TX15_RAM_CHAIN
    uint32_t total=chain_control.bytes;
    if(chain_control.gate!=TX15_CHAIN_GO || !tx15_chain_range(offset,bytes,total))return 0;
    const volatile uint8_t *source=(const volatile uint8_t *)TX15_CHAIN_SOURCE;
    for(uint32_t i=0;i<bytes;i++)dst[i]=source[offset+i];
    return 1;
#else
    return tx15_boot_qspi_read(offset,dst,bytes,1000000u)==TX15_QSPI_OK;
#endif
}
static int copy(void *ctx,const struct tx15_boot_segment *s) {
    (void)ctx;volatile uint32_t *dst=(volatile uint32_t *)s->destination;
    // Explicit doubleword stores initialize every AXI ECC word, including padding.
    for (uint32_t at=0;at<s->length;at+=8) {
        uint32_t words[2]={0,0};
        for (unsigned i=0;i<8 && at+i<s->length;i++)words[i/4]|=(uint32_t)s->source[at+i]<<((i%4)*8);
        __asm volatile("strd %1,%2,[%0]"::"r"(dst),"r"(words[0]),"r"(words[1]):"memory");
        dst+=2;
    }
    __asm volatile("dsb":::"memory");return 1;
}
static int verify(void *ctx,const struct tx15_boot_segment *s) {
    (void)ctx;const volatile uint8_t *dst=(const volatile uint8_t *)s->destination;
    for(uint32_t i=0;i<s->length;i++)if(dst[i]!=s->source[i])return 0;
    return 1;
}
void tx15_boot_jump(uint32_t entry) __attribute__((noreturn));
void Boot_Main(void) {
    tx15_power_init();
    probe_report.magic=PROBE_MAGIC;probe_report.version=TX15_BOOT_HANDOFF_VERSION;probe_report.state=PROBE_INIT;
    probe_report.cpuid=R(0xe000ed00u);probe_report.device_id=R(0x5c001000u);
    probe_report.rcc_cr=R(0x58024400u);probe_report.rcc_cfgr=R(0x58024410u);
    probe_report.rcc_d1cfgr=R(0x58024418u);probe_report.scb_ccr=R(0xe000ed14u);probe_report.mpu_ctrl=R(0xe000ed94u);
    probe_report.power_status=tx15_power_status();
    uint32_t environment=probe_environment_error(&probe_report);
    if(environment || (probe_report.power_status&15u)!=15u)fail(environment|BAD_POWER);
    // Explicitly keep the verified internal module power pin PB13 off.
    R(0x580244e0u)|=2u;(void)R(0x580244e0u);R(0x58020418u)=1u<<29;
    R(0x58020404u)&=~(1u<<13);R(0x58020400u)=(R(0x58020400u)&~(3u<<26))|(1u<<26);
    enum tx15_clock_result clock=tx15_boot_clock_init(1000000u);
    if(clock!=TX15_CLOCK_OK)fail(BAD_CLOCK|((uint32_t)clock<<8));
    probe_report.ram_words=TX15_BOOT_CLOCK;
    if(tx15_sdram_init(&probe_report.sdram))fail(BAD_SDRAM);
    probe_report.ram_words|=TX15_BOOT_SDRAM;
    uint32_t id=0;enum tx15_qspi_result qspi=tx15_boot_qspi_init(&id,1000000u);
    if(qspi!=TX15_QSPI_OK || id!=0xc84018u) {tx15_boot_qspi_stop();fail(256u|((uint32_t)qspi<<16));}
#ifdef TX15_RAM_CHAIN
    // Exercise the actual read-only driver; original NOR remains untouched.
    uint8_t prefix[64];
    if(tx15_boot_qspi_read(0,prefix,sizeof(prefix),1000000u)!=TX15_QSPI_OK) {
        tx15_boot_qspi_stop();fail(256u);
    }
    for(unsigned i=0;i<64;i++)chain_control.original_prefix[i]=prefix[i];
    tx15_boot_qspi_stop();chain_control.jedec=id;
    __asm volatile("dsb":::"memory");chain_control.ready=TX15_CHAIN_READY;
    // Host fills a separate source buffer after SDRAM initialization, then
    // opens the gate. Staging, validation, STRD copies and jump stay native.
    while(chain_control.gate!=TX15_CHAIN_GO)__asm volatile("nop");
    __asm volatile("dsb\nisb":::"memory");
#endif
    struct tx15_boot_io io={0,read_image,copy,verify};uint32_t entry=0;
    enum tx15_boot_load_result load=tx15_boot_load(&io,TX15_BOOT_SLOT_OFFSET,TX15_BOOT_SLOT_BYTES,
        (uint8_t *)TX15_BOOT_STAGING,TX15_BOOT_MAX_BYTES,&entry);
    tx15_boot_qspi_stop();
    if(load!=TX15_BOOT_LOAD_OK)fail(512u|((uint32_t)load<<16));
    probe_report.ram_words|=TX15_BOOT_IMAGE|TX15_BOOT_COPIED;
    tx15_display_fill(0);unsigned display=tx15_display_init();
    if(display)fail(128u|(display<<8));
    probe_report.ram_words|=TX15_BOOT_DISPLAY;
    probe_report.rcc_cr=R(0x58024400u);probe_report.rcc_cfgr=R(0x58024410u);probe_report.rcc_d1cfgr=R(0x58024418u);
    probe_report.state=PROBE_RUNNING;
    if(!tx15_boot_handoff_valid(&probe_report))fail(1024u);
    R(0xe000e010u)=0;R(0xe000e014u)=0;R(0xe000e018u)=0;R(0xe000ed04u)=(1u<<25)|(1u<<27);
    for(unsigned i=0;i<8;i++) {R(0xe000e180u+i*4)=0xffffffffu;R(0xe000e280u+i*4)=0xffffffffu;}
    __asm volatile("dsb\nisb":::"memory");tx15_boot_jump(entry);
}
