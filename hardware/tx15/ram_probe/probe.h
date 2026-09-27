/* New Deviation hardware bring-up; GPL-3.0-or-later. */
#ifndef NEW_DEVIATION_RAM_PROBE_H
#define NEW_DEVIATION_RAM_PROBE_H
#include <stdint.h>

#define PROBE_MAGIC 0x4e445631u
#define PROBE_VERSION 3u
#define PROBE_RAM_WORDS 512u
enum probe_state { PROBE_INIT = 1, PROBE_RAM_OK, PROBE_RUNNING, PROBE_ERROR, PROBE_FAULT };
enum probe_error { BAD_CORE = 1, BAD_DEVICE = 2, BAD_CLOCK = 4, BAD_CPU_STATE = 8, BAD_RAM = 16, BAD_POWER = 32 };

struct probe_report {
    uint32_t magic, version, state, error;
    uint32_t cpuid, device_id, rcc_cr, rcc_cfgr, rcc_d1cfgr, scb_ccr, mpu_ctrl;
    uint32_t ticks, loops, ram_words;
    uint32_t fault_exception, cfsr, hfsr, mmfar, bfar, power_status;
};

/* Require reset-like clock/CPU conditions; never silently assume a timer frequency. */
static inline uint32_t probe_environment_error(const volatile struct probe_report *r)
{
    uint32_t error = 0;
    if (((r->cpuid >> 4) & 0xfffu) != 0xc27u) error |= BAD_CORE;
    /* 0x450 identifies the H742/H743/H750/H753 family, not a unique part/package. */
    if ((r->device_id & 0xfffu) != 0x450u) error |= BAD_DEVICE;
    if ((r->rcc_cr & 0x1du) != 5u || (r->rcc_cfgr & 0x3fu) || (r->rcc_d1cfgr & 0xf0fu))
        error |= BAD_CLOCK;
    if ((r->scb_ccr & ((1u << 16) | (1u << 17))) || (r->mpu_ctrl & 1u))
        error |= BAD_CPU_STATE;
    return error;
}
#endif
