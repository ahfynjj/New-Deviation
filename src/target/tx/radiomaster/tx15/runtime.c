/* Services shared by the main loop and original blocking calibration page. */
#include "common.h"
#include "runtime.h"
#include "../../../../../hardware/tx15/board/battery.h"
#include "rf.h"
#ifdef TX15_ELRS_LUA
#include "rf_lua.h"
#endif
#ifdef TX15_ELRS_RC
#include "rf_model.h"
#endif
#include "../../../../../hardware/tx15/board/analog.h"
#include "../../../../../hardware/tx15/board/controls.h"
#ifdef TX15_TOUCH_DIAGNOSTIC
#include "../../../../../hardware/tx15/board/touch.h"
#endif
#ifdef TX15_STORAGE
#include "storage_tool.h"
#endif
#ifdef TX15_AUDIO
#include "../../../../../hardware/tx15/board/audio.h"
#endif
int tx15_runtime_poll(unsigned now) {
#ifdef TX15_STANDALONE
    tx15_battery_poll(now);
#endif
#ifdef TX15_ELRS_LUA
    tx15_rf_lua_poll();
#endif
#ifdef TX15_ELRS_DISCOVERY
    tx15_rf_discovery_poll(now);
#endif
    static unsigned sampled, refreshed;
#ifdef TX15_STORAGE
    tx15_storage_poll(now);
#endif
#ifdef TX15_AUDIO
    tx15_audio_hw_poll(now);
#endif
    if((u32)(now-sampled)<MEDIUM_PRIORITY_MSEC) {
#ifdef TX15_TOUCH_DIAGNOSTIC
        tx15_touch_poll(now);
#endif
        return 0;
    }
    sampled=now;
    tx15_controls_poll(now);
    tx15_analog_sample();
#ifdef TX15_ELRS_RC
    tx15_rf_model_service(now);
#endif
    priority_ready|=1u<<MEDIUM_PRIORITY;
    if((u32)(now-refreshed)>=LOW_PRIORITY_MSEC) {
        refreshed=now;
        priority_ready|=1u<<LOW_PRIORITY;
    }
#ifdef TX15_TOUCH_DIAGNOSTIC
    tx15_touch_poll(now); /* Main-thread I2C only; never dispatch GUI/Lua here. */
#endif
    return 1;
}
