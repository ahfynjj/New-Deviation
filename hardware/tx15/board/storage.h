/* Native SDMMC1 read-only probe; GPL-3.0-or-later. */
#ifndef TX15_STORAGE_H
#define TX15_STORAGE_H
#include "../../../src/storage/card.h"
extern const struct nd_sd_ops tx15_storage_ops;
struct tx15_storage_hw_report {
    uint32_t status,response,commands,reads,reason;
    uint32_t clkcr,power,cmd,pllcfgr,selector;
};
extern volatile struct tx15_storage_hw_report tx15_storage_hw_report;
#endif
