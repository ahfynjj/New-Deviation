#include "crsf_rc.h"
#include <string.h>
void crsf_rc_init(struct crsf_rc *rc) {memset(rc,0,sizeof(*rc));}
int crsf_rc_select(struct crsf_rc *rc,int slot,uint32_t now) {
    crsf_rc_init(rc);rc->report.last_ms=now;
    if(slot==CRSF_SLOT_OFF)return 1;
    if(slot!=CRSF_SLOT_INTERNAL)return 0;
    rc->report.active=1;return 1;
}
int crsf_rc_publish(struct crsf_rc *rc,const int32_t *ch,unsigned count,uint32_t now) {
    if(!rc->report.active || !ch || !count || count>16)return 0;
    /* Reuse the established encoder outside IRQ; link state is temporary and
     * never shared with the Lua/router queues. */
    struct crsf_link packed;crsf_link_init(&packed);
    crsf_link_select(&packed,CRSF_SLOT_INTERNAL);
    crsf_link_set_channels(&packed,ch,count);
    rc->frame=packed.rc;rc->report.sample_ms=now;rc->report.published++;rc->fresh=1;
    return 1;
}
static int valid(const struct crsf_rc *rc,uint32_t now) {
    return rc->report.active && rc->fresh && now-rc->report.sample_ms<CRSF_RC_STALE_MS;
}
int crsf_rc_tools_ready(const struct crsf_rc *rc,uint32_t now) {
    if(!valid(rc,now))return 1;
    return rc->sent && now-rc->report.last_ms<CRSF_RC_PERIOD_MS-2;
}
void crsf_rc_tick(struct crsf_rc *rc,uint32_t now,crsf_rc_send send,void *ctx) {
    if(!rc->report.active || !rc->fresh)return;
    if(!valid(rc,now)) {rc->fresh=0;rc->report.stale++;return;}
    if(rc->sent && now-rc->report.last_ms<CRSF_RC_PERIOD_MS)return;
    if(!send || !send(ctx,rc->frame.bytes,rc->frame.size)) {rc->report.busy++;return;}
    if(rc->sent && now-rc->report.last_ms>rc->report.max_gap_ms)
        rc->report.max_gap_ms=now-rc->report.last_ms;
    rc->sent=1;rc->report.last_ms=now;rc->report.frames++;
}
