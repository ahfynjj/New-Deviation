/* Services shared by the main loop and original blocking calibration page. */
#include "common.h"
#include "runtime.h"
#include "../../../../../hardware/tx15/board/analog.h"
int tx15_runtime_poll(unsigned now) {
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
