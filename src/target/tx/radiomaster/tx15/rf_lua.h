#ifndef TX15_RF_LUA_H
#define TX15_RF_LUA_H
#include "protocol/transport/crsf_link.h"
#include "protocol/transport/crsf_tools.h"
extern volatile struct crsf_tool_report tx15_rf_write_report;
const char *tx15_rf_lua_error(void);
struct crsf_link *tx15_rf_lua_init(void);
struct crsf_link *tx15_rf_lua_select(int slot);
void tx15_rf_lua_shutdown(void);
void tx15_rf_lua_poll(void);
void tx15_rf_lua_stop(void);
int tx15_rf_lua_authorize(uint8_t,const uint8_t *,unsigned);
int tx15_rf_lua_writes_enabled(void);
int tx15_rf_tools_slot(void);
#endif
