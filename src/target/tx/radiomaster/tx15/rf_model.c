#ifdef TX15_ELRS_RC
#include "common.h"
#include "config/model.h"
#include "rf_model.h"
#include "rf_rc.h"
#include "../../../../../hardware/tx15/board/analog.h"
#ifdef TX15_ELRS_PRODUCT
static int ready,selected[2]={-2,-2};
static unsigned released[2];
volatile uint32_t tx15_rf_throttle_wait;
void tx15_rf_model_start(uint32_t now) {(void)now;ready=1;selected[0]=selected[1]=-2;released[0]=released[1]=0;tx15_rf_throttle_wait=0;}
void tx15_rf_model_reset(void) {
    tx15_rf_module_enable(0,0,0);tx15_rf_module_enable(1,0,0);selected[0]=selected[1]=-2;released[0]=released[1]=0;tx15_rf_throttle_wait=0;
}
void tx15_rf_model_service(uint32_t now) {
    if(!ready)return;
    MIXER_CalcChannels();
    int32_t ch[16];
    unsigned count=Model.num_channels;
    if(count>16)count=16;
    for(unsigned i=0;i<count;i++)ch[i]=Channels[i];
    for(unsigned slot=0;slot<2;slot++) {
        int on=tx15_module_enabled(&Model.tx15_modules[slot]) && Model.num_channels>=5 && Model.num_channels<=16;
        if(on!=selected[slot]) {
            tx15_rf_module_enable(slot,on,now);selected[slot]=on;released[slot]=0;
        }
        if(on && !released[slot] && tx15_analog_status==4
          && CHAN_ReadInput(MIXER_MapChannel(INP_THROTTLE))<=-9500)released[slot]=1;
        if(on && !released[slot])tx15_rf_throttle_wait|=1u<<slot;
        else tx15_rf_throttle_wait&=~(1u<<slot);
        if(on && released[slot])tx15_rf_module_update(slot,ch,count,tx15_analog_status==4,now);
    }
}
#else
static uint32_t started;
static int ready,expired,selected=-2;
void tx15_rf_model_start(uint32_t now) {started=now;ready=1;expired=0;selected=-2;}
void tx15_rf_model_reset(void) {
    tx15_rf_rc_select(-1,0);selected=-2;
}
void tx15_rf_model_service(uint32_t now) {
    if(!ready)return;
#ifndef TX15_ELRS_PRODUCT
    if(now-started>=180000)expired=1;
#endif
    int slot=-1;
    if(!expired && tx15_module_enabled(&Model.tx15_modules[0]) && Model.num_channels>=5
       && Model.num_channels<=16)slot=0;
    if(slot!=selected) {tx15_rf_rc_select(slot,now);selected=slot;}
    MIXER_CalcChannels();
    if(slot==0) {
        int32_t ch[16];for(unsigned i=0;i<Model.num_channels;i++)ch[i]=Channels[i];
        tx15_rf_rc_update(ch,Model.num_channels,tx15_analog_status==4,now);
    }
}
#endif

#endif
