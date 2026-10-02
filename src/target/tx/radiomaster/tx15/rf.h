/* Read-only CRSF discovery bench, GPL-3.0-or-later. */
#ifndef TX15_RF_H
#define TX15_RF_H
#include <stdint.h>
#include "protocol/transport/crsf_stream.h"
/* 0=off,1=waiting,2=device found,3=timeout,4=UART init failed */
struct tx15_rf_report {
    uint32_t state,pings,frames,rx_bytes,tx_bytes,errors,dropped;
    struct crsf_device device;
};
extern volatile struct tx15_rf_report tx15_rf_report;
void tx15_rf_discovery_init(uint32_t now);
void tx15_rf_discovery_poll(uint32_t now);
#endif
