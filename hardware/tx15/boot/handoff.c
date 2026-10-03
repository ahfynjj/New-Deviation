#include "handoff.h"
int tx15_boot_handoff_valid(const volatile struct probe_report *r) {
    return r && r->magic==PROBE_MAGIC && r->version==TX15_BOOT_HANDOFF_VERSION
        && r->state==PROBE_RUNNING && !r->error && r->cpuid==0x411fc271u
        && (r->device_id&0xfffu)==0x450u && (r->rcc_cr&0x3f0f001du)==0x33030005u
        && (r->rcc_cfgr&0x3fu)==0x1bu && (r->rcc_d1cfgr&0xf7fu)==0x48u
        && !(r->scb_ccr&0x30000u) && !(r->mpu_ctrl&1u) && r->ram_words==TX15_BOOT_READY
        && !r->fault_exception && !r->cfsr && !r->hfsr && !r->mmfar && !r->bfar
        && (r->power_status&15u)==15u && r->sdram.state==2 && !r->sdram.error;
}
