/* New Deviation TX15; GPL-3.0-or-later. */
#include "inputs.h"
void tx15_input_filter_init(struct tx15_input_filter *f,unsigned keys,unsigned phase) {
    f->stable=f->candidate=keys&4095; f->phase=phase&3; f->partial=0;
    for(unsigned i=0;i<12;i++) f->age[i]=0;
}
struct tx15_input_event tx15_input_filter_step(struct tx15_input_filter *f,unsigned keys,unsigned phase) {
    struct tx15_input_event e={0,0};
    for(unsigned i=0;i<12;i++) {
        unsigned mask=1u<<i;
        if((keys^f->candidate)&mask) { f->candidate^=mask; f->age[i]=0; }
        if(f->age[i]<20) f->age[i]++;
        if(f->age[i]==20 && ((f->stable^f->candidate)&mask)) {
            f->stable^=mask; if(f->stable&mask) e.pressed|=mask;
        }
    }
    /* Four Gray-code edges per step. Reject skipped states instead of guessing
     * motion. TX15 wiring is inverted: 3 -> 1 -> 0 -> 2 -> 3 is positive. */
    phase&=3;
    unsigned old=f->phase, diff=old^phase;
    if(diff==3) f->partial=0;
    else if(diff) {
        unsigned next=(old==3)?1:(old==1)?0:(old==0)?2:3;
        f->partial+=(phase==next)?1:-1;
        if(f->partial>=4) { e.rotation=1; f->partial=0; }
        if(f->partial<=-4) { e.rotation=-1; f->partial=0; }
    }
    f->phase=phase;
    if(keys&TX15_ENTER) { f->partial=0; e.rotation=0; }
    return e;
}
