/* Temporary RAM bench for native cold-start prerequisites, not a bootloader. */
#include "../ram_probe/probe.h"
#include "../board/power.h"
#include "cold_start.h"
#include "qspi.h"
#define R(a) (*(volatile uint32_t *)(a))
volatile struct probe_report probe_report __attribute__((section(".mailbox"),aligned(8)));
struct boot_qspi_report { uint32_t result,jedec_id; uint8_t header[64]; };
volatile struct boot_qspi_report boot_qspi_report;
_Static_assert(sizeof(struct probe_report)==128,"Keep RAM diagnostic reservation");
static void stop(void) __attribute__((noreturn));
static void stop(void) { __asm volatile("cpsid i");R(0xe000e010u)=0;for(;;)__asm volatile("nop"); }
void Probe_Fault(void) {
    uint32_t exception;
    __asm volatile("mrs %0,ipsr":"=r"(exception));
    probe_report.fault_exception=exception;
    probe_report.cfsr=R(0xe000ed28u);probe_report.hfsr=R(0xe000ed2cu);
    probe_report.mmfar=R(0xe000ed34u);probe_report.bfar=R(0xe000ed38u);
    probe_report.state=PROBE_FAULT;stop();
}
void SysTick_Handler(void) { probe_report.ticks++; }
void Probe_Main(void) {
    tx15_power_init(); // assert PH12 before lengthy initialization
    probe_report.magic=PROBE_MAGIC;probe_report.version=8;probe_report.state=PROBE_INIT;
    probe_report.cpuid=R(0xe000ed00u);probe_report.device_id=R(0x5c001000u);
    probe_report.rcc_cr=R(0x58024400u);probe_report.rcc_cfgr=R(0x58024410u);
    probe_report.rcc_d1cfgr=R(0x58024418u);probe_report.scb_ccr=R(0xe000ed14u);
    probe_report.mpu_ctrl=R(0xe000ed94u);probe_report.power_status=tx15_power_status();
    probe_report.error=probe_environment_error(&probe_report);
    if ((probe_report.power_status&TX15_POWER_READY)!=TX15_POWER_READY) probe_report.error|=BAD_POWER;
    if (probe_report.error) { probe_report.state=PROBE_ERROR;stop(); }
    enum tx15_clock_result clock=tx15_boot_clock_init(1000000u);
    probe_report.rcc_cr=R(0x58024400u);probe_report.rcc_cfgr=R(0x58024410u);
    probe_report.rcc_d1cfgr=R(0x58024418u);
    if (clock!=TX15_CLOCK_OK) { probe_report.error=BAD_CLOCK|((uint32_t)clock<<8);probe_report.state=PROBE_ERROR;stop(); }
    uint32_t id=0;
    enum tx15_qspi_result qspi=tx15_boot_qspi_init(&id,1000000u);
    boot_qspi_report.jedec_id=id;
    if (qspi==TX15_QSPI_OK) {
        uint8_t header[64];
        qspi=tx15_boot_qspi_read(0,header,64,1000000u);
        if (qspi==TX15_QSPI_OK) for(unsigned i=0;i<64;i++)boot_qspi_report.header[i]=header[i];
    }
    boot_qspi_report.result=qspi;
    tx15_boot_qspi_stop(); // no QSPI ownership left for original reset-entry recovery
    if(qspi!=TX15_QSPI_OK) {probe_report.error=256u|((uint32_t)qspi<<16);probe_report.state=PROBE_ERROR;stop();}
    R(0xe000e010u)=0;R(0xe000e014u)=TX15_PLL_CORE_HZ/1000u-1;R(0xe000e018u)=0;
    R(0xe000ed04u)=(1u<<25)|(1u<<27);
    probe_report.state=PROBE_RUNNING;R(0xe000e010u)=7;
    __asm volatile("dsb\nisb\ncpsie i":::"memory");
    for(;;) {probe_report.loops++;probe_report.power_status=tx15_power_status();}
}
