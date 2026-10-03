#ifndef TX15_RF_LUA_H
#define TX15_RF_LUA_H
#include "protocol/transport/crsf_link.h"
struct crsf_link *tx15_rf_lua_init(void);
void tx15_rf_lua_poll(void);
void tx15_rf_lua_stop(void);
#endif
