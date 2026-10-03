/* Internal RC bench; RAM only, not flight firmware. GPL-3.0-or-later. */
#ifndef TX15_RF_RC_H
#define TX15_RF_RC_H
#include "protocol/transport/crsf_rc.h"
extern volatile struct crsf_rc_report tx15_rf_rc_report;
int tx15_rf_rc_select(int slot,uint32_t now);
int tx15_rf_rc_enabled(void);
void tx15_rf_rc_update(const int32_t *ch,unsigned count,int analog_ok,uint32_t now);
void tx15_rf_rc_tick(uint32_t now);
int tx15_rf_rc_tools_ready(uint32_t now);
int tx15_rf_rc_send_tool(const uint8_t *data,unsigned size,uint32_t now);
#endif
