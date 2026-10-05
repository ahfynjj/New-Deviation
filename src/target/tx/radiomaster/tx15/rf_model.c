#ifdef TX15_ELRS_RC
#include "common.h"
#include "config/model.h"
#include "rf_model.h"
#include "rf_rc.h"
#include "../../../../../hardware/tx15/board/analog.h"
static uint32_t started;
static int ready,expired,selected=-2;
void tx15_rf_model_start(uint32_t now) {started=now;ready=1;expired=0;selected=-2;}
void tx15_rf_model_reset(void) {
    tx15_rf_rc_select(-1,0);selected=-2;
}
void tx15_rf_model_service(uint32_t now) {
    if(!ready)return;
    if(now-started>=180000)expired=1;
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
