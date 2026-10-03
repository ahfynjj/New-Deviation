/* Periodic latest-sample RC transmitter. GPL-3.0-or-later. */
#ifndef DEVIATION_CRSF_RC_H
#define DEVIATION_CRSF_RC_H
#include "crsf_link.h"
#define CRSF_RC_PERIOD_MS 4u
#define CRSF_RC_STALE_MS 100u
struct crsf_rc_report {
    uint32_t active,published,frames,busy,stale,last_ms,max_gap_ms,sample_ms;
};
struct crsf_rc {
    struct crsf_frame frame;
    struct crsf_rc_report report;
    unsigned fresh,sent;
};
/* Caller serializes publication/selection with tick using a short critical
 * section. Tick only transmits an already packed snapshot, no mixer/Lua/link
 * queues. This initial backend supports internal=0 and off=-1 only. */
void crsf_rc_init(struct crsf_rc *rc);
int crsf_rc_select(struct crsf_rc *rc,int slot,uint32_t now);
int crsf_rc_publish(struct crsf_rc *rc,const int32_t *ch,unsigned count,uint32_t now);
typedef int (*crsf_rc_send)(void *,const uint8_t *,unsigned);
void crsf_rc_tick(struct crsf_rc *rc,uint32_t now,crsf_rc_send send,void *ctx);
/* Reserve 2ms for a maximum 64-byte tool frame at 400k 8N1 (1.6ms).
 * RC due/busy always takes precedence. No claim about RF packet rate. */
int crsf_rc_tools_ready(const struct crsf_rc *rc,uint32_t now);
#endif
