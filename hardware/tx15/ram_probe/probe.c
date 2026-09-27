/* New Deviation hardware bring-up; GPL-3.0-or-later. */
#include "probe.h"
#include "../board/power.h"
#include "../board/clock.h"

#define REG32(addr) (*(volatile uint32_t *)(addr))
#define SYST_CSR REG32(0xe000e010u)
#define SYST_RVR REG32(0xe000e014u)
#define SYST_CVR REG32(0xe000e018u)

volatile struct probe_report probe_report __attribute__((section(".mailbox"), aligned(8)));
static volatile uint32_t scratch[PROBE_RAM_WORDS] __attribute__((aligned(8)));
_Static_assert(sizeof(struct probe_report) == 80, "mailbox ABI must match host decoder");

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
}

void Probe_Main(void)
{
    /* Startup initialized mailbox ECC with aligned doubleword stores. */
    probe_report.version = PROBE_VERSION;
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

    /* Only this owned 2 KiB scratch area is tested, not all internal/external RAM. */
    for (unsigned pass = 0; pass < 2; pass++) {
        for (unsigned i = 0; i < PROBE_RAM_WORDS; i++)
            scratch[i] = (0xa5a50000u ^ i) ^ (pass ? 0xffffffffu : 0u);
        __asm volatile("dsb" ::: "memory");
        for (unsigned i = 0; i < PROBE_RAM_WORDS; i++) {
            if (scratch[i] != ((0xa5a50000u ^ i) ^ (pass ? 0xffffffffu : 0u))) {
                probe_report.error = BAD_RAM;
                probe_report.state = PROBE_ERROR;
                stop();
            }
        }
    }
    probe_report.ram_words = PROBE_RAM_WORDS;
    probe_report.state = PROBE_RAM_OK;
    /* Confirmed PLL128 processor clock, nominal 1 ms. */
    SYST_CSR = 0;
    SYST_RVR = TX15_PLL_CORE_HZ / 1000u - 1u;
    SYST_CVR = 0;
    REG32(0xe000ed04u) = (1u << 25) | (1u << 27); /* clear pending SysTick/PendSV */
    probe_report.state = PROBE_RUNNING;
    SYST_CSR = 7;
    __asm volatile("dsb\nisb\ncpsie i" ::: "memory");
    for (;;) {
        probe_report.loops++;
        probe_report.power_status = tx15_power_status();
    }
}
