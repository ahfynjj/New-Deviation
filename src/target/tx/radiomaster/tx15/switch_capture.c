#include "switch_capture.h"
int tx15_switch_capture_step(struct tx15_switch_capture *c,const struct tx15_controls *inputs,int armed) {
    if(!armed) {c->armed=0;c->seen=0;return 0;}
    unsigned valid=0,count=0;int event=0;
    for(unsigned i=0;i<6;i++) {
        unsigned p=inputs->position[i];
        if((inputs->valid&(1u<<i)) && p<3) {
            valid|=1u<<i;
            if(c->armed && (c->seen&(1u<<i)) && c->previous[i]!=p) {
                event=1+3*i+p;count++;
            }
            c->previous[i]=p;
        }
    }
    c->armed=1;c->seen=valid;
    return count==1?event:0;
}
