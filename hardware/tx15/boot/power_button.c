#include "power_button.h"
int tx15_power_button_poll(struct tx15_power_button *b,uint32_t now,int pressed) {
    if(b->shutdown)return 1;
    if(!b->released) {
        if(pressed)b->tracking=0;
        else if(!b->tracking) {b->tracking=1;b->since=now;}
        else if((uint32_t)(now-b->since)>=20u) {b->released=1;b->tracking=0;}
        return 0;
    }
    if(!pressed)b->tracking=0;
    else if(!b->tracking) {b->tracking=1;b->since=now;}
    else if((uint32_t)(now-b->since)>=2000u)b->shutdown=1;
    return b->shutdown;
}
