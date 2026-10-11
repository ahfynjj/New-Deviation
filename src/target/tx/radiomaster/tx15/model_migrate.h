/* Frozen two-position SE/SF storage layout and RAM-only migration.
 * GPL-3.0-or-later. Never edit v1 fields when extending the current model. */
#ifndef TX15_MODEL_MIGRATE_H
#define TX15_MODEL_MIGRATE_H
#include "config/model.h"
#include "config/tx.h"
#include "../../../../../hardware/tx15/board/settings_snapshot.h"
#include <stddef.h>
#include <string.h>
struct tx15_model_v1 {
    struct tx15_module_setting tx15_modules[2];
    u32 fixed_id;
    enum ModelType type;
    enum Protocols protocol;
    s16 proto_opts[NUM_PROTO_OPTS];
    u8 num_channels,num_ppmin_channels;
    u16 ppmin_centerpw,ppmin_deltapw;
    u8 train_sw;
    enum Radio radio;
    enum TxPower tx_power;
    enum SwashType swash_type;
    u8 swash_invert,swashmix[3];
    char name[24],icon[24],virtname[NUM_VIRT_CHANNELS][VIRT_NAME_LEN];
    u8 templates[NUM_CHANNELS];
    u8 safety[28+NUM_CHANNELS+MAX_PPM_IN_CHANNELS+1];
    MixerMode mixer_mode;
    s8 ppm_map[MAX_PPM_IN_CHANNELS];
    u8 ppmin_mode,padding_1[1];
    u32 permanent_timer;
    struct TelemetryAlarm alarms[TELEM_NUM_ALARMS];
    struct Trim trims[NUM_TRIMS];
    struct Mixer mixers[NUM_MIXERS];
    struct Limit limits[NUM_OUT_CHANNELS];
    struct Timer timer[NUM_TIMERS];
    struct PageCfg2 pagecfg2;
    s32 ground_level;
};
#ifdef __arm__
_Static_assert(sizeof(struct tx15_model_v1)==3400,"frozen ARM v1 model ABI");
#endif
/* Old E/F position 0 meant both contacts open (now the centre). Position 1
 * combined both ends; migrate it to the upper end. Users with E/F mixes must
 * review that assignment, since a collapsed two-end predicate is ambiguous. */
static inline unsigned tx15_source_from_v1(unsigned value) {
    unsigned src=value&0x7fu,inv=value&0x80u;
    return inv|(src<=18?src:src<=20?src+1:src+2);
}
static inline void tx15_model_from_v1(struct Model *out,const struct tx15_model_v1 *old) {
    _Static_assert(offsetof(struct Model,safety)==offsetof(struct tx15_model_v1,safety),"v1 prefix ABI");
    _Static_assert(sizeof(struct Model)-offsetof(struct Model,permanent_timer)==
        sizeof(struct tx15_model_v1)-offsetof(struct tx15_model_v1,permanent_timer),"v1 tail ABI");
    memset(out,0,sizeof(*out));
    memcpy(out,old,offsetof(struct Model,safety));
    /* The larger byte safety array changes the following ARM alignment gap.
     * Copy its byte fields individually, then the word-aligned unchanged tail. */
    out->mixer_mode=old->mixer_mode;out->ppmin_mode=old->ppmin_mode;
    memcpy(out->ppm_map,old->ppm_map,sizeof(out->ppm_map));
    memcpy((u8*)out+offsetof(struct Model,permanent_timer),
        (const u8*)old+offsetof(struct tx15_model_v1,permanent_timer),
        sizeof(*out)-offsetof(struct Model,permanent_timer));
    for(unsigned i=0;i<sizeof(old->safety);i++)out->safety[tx15_source_from_v1(i)]=old->safety[i];
    out->train_sw=tx15_source_from_v1(out->train_sw);
    for(unsigned i=0;i<NUM_TRIMS;i++) {
        out->trims[i].src=tx15_source_from_v1(out->trims[i].src);
        out->trims[i].sw=tx15_source_from_v1(out->trims[i].sw);
    }
    for(unsigned i=0;i<NUM_MIXERS;i++) {
        out->mixers[i].src=tx15_source_from_v1(out->mixers[i].src);
        out->mixers[i].sw=tx15_source_from_v1(out->mixers[i].sw);
    }
    for(unsigned i=0;i<NUM_OUT_CHANNELS;i++)out->limits[i].safetysw=tx15_source_from_v1(out->limits[i].safetysw);
    for(unsigned i=0;i<NUM_TIMERS;i++) {
        out->timer[i].src=tx15_source_from_v1(out->timer[i].src);
        out->timer[i].resetsrc=tx15_source_from_v1(out->timer[i].resetsrc);
    }
    /* Bars/boxes use channel indices, trims use trim indices: only toggles
     * contain the global input source enumeration. */
    for(unsigned i=0;i<NUM_ELEMS;i++)if(ELEM_TYPE(out->pagecfg2.elem[i])==ELEM_TOGGLE)
        out->pagecfg2.elem[i].src=tx15_source_from_v1(out->pagecfg2.elem[i].src);
}
static inline int tx15_model_restore(struct Model *out,struct Transmitter *tx,unsigned id,
    int (*read)(unsigned,void*,unsigned)) {
    static union {
        struct {struct tx15_snapshot_header header;struct Model model;} v2;
        struct {struct tx15_snapshot_header header;struct tx15_model_v1 model;} v1;
        struct tx15_model_v1 raw;
    } saved;
    const struct tx15_snapshot_header *header=0;
    if(read(id,&saved.v2,sizeof(saved.v2)) && saved.v2.header.version==2
        && tx15_snapshot_valid(&saved.v2.header,sizeof(struct Model))) {
        *out=saved.v2.model;header=&saved.v2.header;
    } else if(read(id,&saved.v1,sizeof(saved.v1)) && saved.v1.header.version==1
        && tx15_snapshot_valid(&saved.v1.header,sizeof(struct tx15_model_v1))) {
        tx15_model_from_v1(out,&saved.v1.model);header=&saved.v1.header;
    } else if(read(id,&saved.raw,sizeof(saved.raw))) {
        tx15_model_from_v1(out,&saved.raw);return 1;
    } else return 0;
    tx->mode=header->mode;
    for(unsigned i=0;i<6;i++) {
        tx->calibration[i].max=header->cal[i][0];
        tx->calibration[i].min=header->cal[i][1];
        tx->calibration[i].zero=header->cal[i][2];
    }
    return 1;
}
#endif
