/* Read-only CRSF discovery bench, GPL-3.0-or-later. */
#ifndef TX15_RF_H
#define TX15_RF_H
#include <stdint.h>
#include "protocol/transport/crsf_stream.h"
#include "protocol/transport/crsf_params.h"
/* 0=off,1=waiting,2=done,3=timeout,4=UART init failed,5=reading,6=invalid */
struct tx15_rf_report {
    uint32_t state,pings,frames,rx_bytes,tx_bytes,errors,dropped;
    struct crsf_device device;
    uint32_t completed,requests,retries,active_errors,active_dropped,failed_id;
};
extern volatile struct tx15_rf_report tx15_rf_report;
extern struct crsf_params tx15_rf_parameters;
void tx15_rf_discovery_init(uint32_t now);
void tx15_rf_discovery_poll(uint32_t now);
#endif
