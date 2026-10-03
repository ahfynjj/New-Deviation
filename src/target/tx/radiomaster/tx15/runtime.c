/* Services shared by the main loop and original blocking calibration page. */
#include "common.h"
#include "runtime.h"
#include "rf.h"
#ifdef TX15_ELRS_LUA
#include "rf_lua.h"
#endif
#include "../../../../../hardware/tx15/board/analog.h"
int tx15_runtime_poll(unsigned now) {
#ifdef TX15_ELRS_LUA
    tx15_rf_lua_poll();
#endif
#ifdef TX15_ELRS_DISCOVERY
    tx15_rf_discovery_poll(now);
#endif
    static unsigned sampled, refreshed;
    if((u32)(now-sampled)<MEDIUM_PRIORITY_MSEC) return 0;
    sampled=now;
    tx15_analog_sample();
    priority_ready|=1u<<MEDIUM_PRIORITY;
    if((u32)(now-refreshed)>=LOW_PRIORITY_MSEC) {
        refreshed=now;
        priority_ready|=1u<<LOW_PRIORITY;
    }
    return 1;
}
