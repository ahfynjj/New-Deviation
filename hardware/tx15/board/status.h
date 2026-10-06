/* Native battery and CRSF status helpers; GPL-3.0-or-later. */
#ifndef TX15_STATUS_H
#define TX15_STATUS_H
#include "protocol/transport/crsf_link.h"
struct tx15_link_status { uint32_t last_ms; int rssi_dbm; unsigned lq,valid; };
static inline unsigned tx15_battery_scale(unsigned raw) {
 return raw<=4095 ? (raw*3300u*132u+4095u*16u)/(4095u*32u) : 0;
}
static inline int tx15_status_frame(struct tx15_link_status *s,const struct crsf_frame *f,uint32_t now) {
 if(!crsf_frame_valid(f) || f->bytes[2]!=0x14 || f->size!=14 || f->bytes[5]>100)return 0;
 s->rssi_dbm=-(int)f->bytes[3];s->lq=f->bytes[5];s->last_ms=now;s->valid=1;return 1;
}
static inline int tx15_status_connected(const struct tx15_link_status *s,uint32_t now) {
 return s->valid && s->lq && (uint32_t)(now-s->last_ms)<=3000;
}
#endif
