/* Pin facts: fixed TX15 hw_defs and bsp_io.h; independent Deviation decoder.
 * 0x74: six buttons + trims; 0x75: SA-SF. GPL-3.0-or-later. */
#include "controls.h"
void tx15_controls_invalidate(struct tx15_controls *c) {
    c->valid=0; c->trims=0;
    for(unsigned i=0;i<6;i++) c->candidate[i]=255;
    c->buttons=0; c->buttons_candidate=64;
}
void tx15_controls_reset(struct tx15_controls *c) {
    for(unsigned i=0;i<7;i++) c->position[i]=0;
    for(unsigned i=0;i<6;i++) c->since[i]=0;
    c->buttons_since=0; tx15_controls_invalidate(c);
}
void tx15_controls_decode(struct tx15_controls *c,uint16_t port74,uint16_t port75,unsigned now) {
    static const unsigned hi[6]={13,11,9,7,15,4},lo[6]={12,10,8,6,14,5};
    static const unsigned trim[8]={12,13,10,11,15,14,9,8};
    unsigned trims=0;
    for(unsigned i=0;i<8;i++) if(!(port74&(1u<<trim[i]))) trims|=1u<<i;
    c->trims=trims; /* Publish once: SysTick must not observe a partial mask. */
    for(unsigned i=0;i<6;i++) {
        unsigned h=(port75>>hi[i])&1,l=(port75>>lo[i])&1;
        unsigned p=(!h && !l)?255:(i<4?(h?(l?1:0):2):(!(h&&l)));
        if(p==255) { c->candidate[i]=255; c->valid&=~(1u<<i); continue; }
        if(c->candidate[i]!=p) { c->candidate[i]=p;c->since[i]=now; }
        if((uint32_t)(now-c->since[i])>=20) {c->position[i]=p;c->valid|=1u<<i;}
    }
    unsigned buttons=(~port74)&63;
    if(c->buttons_candidate!=buttons) {c->buttons_candidate=buttons;c->buttons_since=now;}
    if((uint32_t)(now-c->buttons_since)>=20) {
        unsigned pressed=buttons&~c->buttons;
        c->buttons=buttons; c->valid|=1u<<6;
        if(pressed && !(buttons&(buttons-1)))
            for(unsigned i=0;i<6;i++) if(buttons==(1u<<i)) c->position[6]=i;
    }
}
int tx15_controls_switch(const struct tx15_controls *c,unsigned group,unsigned position) {
    if(group>=7 || position>=(group<4?3:group<6?2:6) || !(c->valid&(1u<<group))) return -1;
    return c->position[group]==position;
}
