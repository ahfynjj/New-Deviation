/* Repair only models with entirely unconfigured trims; GPL-3.0-or-later. */
#ifndef TX15_TRIM_DEFAULTS_H
#define TX15_TRIM_DEFAULTS_H
static inline int tx15_trim_defaults(struct Model *model) {
    for(unsigned i=0;i<NUM_TRIMS;i++) {
        const struct Trim *t=&model->trims[i];
        if(t->src || t->pos || t->neg || t->sw || t->step>1)return 0;
        for(unsigned j=0;j<6;j++)if(t->value[j])return 0;
    }
    /* Physical stick axes, before MIXER_MapChannel applies the selected mode. */
    static const unsigned src[]={2,3,4,1};
    for(unsigned i=0;i<4;i++) {
        model->trims[i].src=src[i];
        model->trims[i].neg=1+2*i;model->trims[i].pos=2+2*i;
        model->trims[i].step=1;
    }
    return 1;
}
#endif
