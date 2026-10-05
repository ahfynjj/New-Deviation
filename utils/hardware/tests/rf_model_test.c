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
#ifdef TX15_ELRS_PRODUCT
static int external;static int throttle=-10000;
s32 CHAN_ReadInput(int ch) {(void)ch;return throttle;}
unsigned MIXER_MapChannel(unsigned ch) {return ch;}
int tx15_rf_module_active(unsigned slot) {return slot?external:enabled;}
int tx15_rf_module_enable(unsigned slot,int on,uint32_t ms) {
 if(slot) {external=on;return 1;}
 return tx15_rf_rc_select(on?0:-1,ms);
}
void tx15_rf_module_update(unsigned slot,const int32_t *ch,unsigned n,int ok,uint32_t ms) {
 if(!slot)tx15_rf_rc_update(ch,n,ok,ms);
}
#endif
void MIXER_CalcChannels(void) {mixed++;}
int main(void) {
    Model.protocol=PROTOCOL_CRSF;Model.tx15_modules[0].protocol=1;Model.num_channels=7;tx15_analog_status=4;
    tx15_rf_model_service(0);assert(!opened && !mixed);
    tx15_rf_model_start(1);tx15_rf_model_service(5);assert(!opened && mixed==1);
#ifdef TX15_ELRS_PRODUCT
    Model.tx15_modules[1].enabled=1;Model.tx15_modules[1].protocol=1;
#endif
    Model.tx15_modules[0].enabled=1;tx15_rf_model_service(10);assert(opened==1 && published==1);
    tx15_rf_model_service(15);assert(opened==1 && published==2);
#ifdef TX15_ELRS_PRODUCT
    assert(external);
#endif
    tx15_rf_model_reset();assert(!enabled);
    tx15_rf_model_service(20);assert(opened==2);
    Model.tx15_modules[0].enabled=2;tx15_rf_model_service(25);assert(!enabled && opened==2);
    Model.tx15_modules[0].enabled=1;Model.num_channels=4;tx15_rf_model_service(30);assert(!enabled);
    Model.num_channels=7;tx15_rf_model_service(35);assert(opened==3);
    Model.tx15_modules[0].protocol=0;tx15_rf_model_service(40);assert(!enabled);
    Model.tx15_modules[0].protocol=1;tx15_rf_model_service(45);assert(enabled);
    tx15_rf_model_service(180001);
#ifdef TX15_ELRS_PRODUCT
    assert(enabled);
#else
    assert(!enabled);
#endif
    Model.tx15_modules[0].enabled=0;tx15_rf_model_service(180005);
    Model.tx15_modules[0].enabled=1;tx15_rf_model_service(180010);
#ifdef TX15_ELRS_PRODUCT
    assert(enabled && closed);
#else
    assert(!enabled && closed);
#endif
#ifdef TX15_ELRS_PRODUCT
    tx15_rf_model_reset();throttle=0;
    unsigned before=published;tx15_rf_model_service(180020);assert(enabled && published==before);
    throttle=-10000;tx15_rf_model_service(180030);assert(published==before+1);
    throttle=10000;tx15_rf_model_service(180040);assert(published==before+2);
#endif

}
