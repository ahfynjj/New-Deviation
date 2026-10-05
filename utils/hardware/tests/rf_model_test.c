#include <assert.h>
#include "common.h"
#include "config/model.h"
#include "rf_model.h"
#include "rf_rc.h"
#include "hardware/tx15/board/analog.h"
struct Model Model;
volatile s32 Channels[NUM_OUT_CHANNELS];
volatile uint32_t tx15_analog_status;
static unsigned opened,closed,published,mixed;
static int enabled;
int tx15_rf_rc_select(int slot,uint32_t now) {
    (void)now;enabled=slot==0;
    if(enabled)opened++;else closed++;
    return slot==0 || slot==-1;
}
int tx15_rf_rc_enabled(void) {return enabled;}
void tx15_rf_rc_update(const int32_t *ch,unsigned count,int ok,uint32_t now) {
    (void)ch;(void)now;assert(count==7);if(ok && enabled)published++;
}
void MIXER_CalcChannels(void) {mixed++;}
int main(void) {
    Model.protocol=PROTOCOL_CRSF;Model.tx15_modules[0].protocol=1;Model.num_channels=7;tx15_analog_status=4;
    tx15_rf_model_service(0);assert(!opened && !mixed);
    tx15_rf_model_start(1);tx15_rf_model_service(5);assert(!opened && mixed==1);
    Model.tx15_modules[0].enabled=1;tx15_rf_model_service(10);assert(opened==1 && published==1);
    tx15_rf_model_service(15);assert(opened==1 && published==2);
    tx15_rf_model_reset();assert(!enabled);
    tx15_rf_model_service(20);assert(opened==2);
    Model.tx15_modules[0].enabled=2;tx15_rf_model_service(25);assert(!enabled && opened==2);
    Model.tx15_modules[0].enabled=1;Model.num_channels=4;tx15_rf_model_service(30);assert(!enabled);
    Model.num_channels=7;tx15_rf_model_service(35);assert(opened==3);
    Model.tx15_modules[0].protocol=0;tx15_rf_model_service(40);assert(!enabled);
    Model.tx15_modules[0].protocol=1;tx15_rf_model_service(45);assert(enabled);
    tx15_rf_model_service(180001);assert(!enabled);
    Model.tx15_modules[0].enabled=0;tx15_rf_model_service(180005);
    Model.tx15_modules[0].enabled=1;tx15_rf_model_service(180010);assert(!enabled && closed);
}
