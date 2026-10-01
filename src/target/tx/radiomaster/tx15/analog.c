/* Native analog input mapping; GPL-3.0-or-later. RF remains disabled. */
#include "common.h"
#include "config/tx.h"
#include "../../../../../hardware/tx15/board/analog.h"
/* Physical sticks first; MIXER_MapChannel applies Transmitter.mode afterward. */
static const unsigned index_map[6]={3,1,2,0,4,5};
static const unsigned inverted[6]={1,1,0,0,1,1};
s32 CHAN_ReadRawInput(int ch) {
    if(ch<1 || ch>6 || tx15_analog_status!=4) return 0;
    unsigned value=tx15_analog_raw[index_map[ch-1]];
    return inverted[ch-1]?4095-value:value;
}
s32 CHAN_ReadInput(int ch) {
    if(ch<1 || ch>6) return 0; /* switches follow after analog acceptance */
    if(tx15_analog_status!=4) return ch==INP_THROTTLE?CHAN_MIN_VALUE:0;
    const struct StickCalibration *c=&Transmitter.calibration[ch-1];
    s32 lo=c->min,mid=c->zero,hi=c->max;
    if(!(lo<mid && mid<hi && hi<=4095)) { lo=0;mid=2048;hi=4095; }
    s32 value=CHAN_ReadRawInput(ch);
    value=(value-mid)*CHAN_MAX_VALUE/(value>=mid?hi-mid:mid-lo);
    if(value<CHAN_MIN_VALUE) value=CHAN_MIN_VALUE;
    if(value>CHAN_MAX_VALUE) value=CHAN_MAX_VALUE;
    return value;
}
