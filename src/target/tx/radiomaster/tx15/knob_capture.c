#include "knob_capture.h"
int tx15_knob_capture_step(struct tx15_knob_capture *c,const int values[2],int valid,int armed) {
    if(!armed || !valid) {c->seeded=0;return 0;}
    if(!c->seeded) {
        for(unsigned i=0;i<2;i++)c->baseline[i]=values[i];
        c->seeded=1;return 0;
    }
    unsigned count=0,event=0;
    for(unsigned i=0;i<2;i++) {
        int delta=values[i]-c->baseline[i];
        if(delta>=TX15_KNOB_CAPTURE_DELTA || delta<=-TX15_KNOB_CAPTURE_DELTA) {
            c->baseline[i]=values[i];count++;event=i+1;
        }
    }
    return count==1?(int)event:0;
}
