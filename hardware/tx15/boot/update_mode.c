/* Pure policies, tested independently of hardware; GPL-3.0-or-later. */
#include "update_mode.h"
int tx15_boot_update_mode(unsigned exit_stable,enum tx15_boot_load_result result)
{
    switch(result) {
    case TX15_BOOT_LOAD_OK: return !!exit_stable;
    case TX15_BOOT_LOAD_READ_ERROR:
    case TX15_BOOT_LOAD_BAD_IMAGE: return 1;
    default: return 0;
    }
}
int tx15_update_power_poll(struct tx15_update_power *p,uint32_t now,unsigned pressed,unsigned busy)
{
    if(busy) { p->phase=0;return 0; }
    switch(p->phase) {
    case 0: if(!pressed) {p->since=now;p->phase=1;} break;
    case 1:
        if(pressed) p->phase=0;
        else if((uint32_t)(now-p->since)>=20) p->phase=2;
        break;
    case 2: if(pressed) {p->since=now;p->phase=3;} break;
    case 3:
        if(!pressed) {p->since=now;p->phase=1;}
        else if((uint32_t)(now-p->since)>=2000) return 1;
        break;
    default: p->phase=0;
    }
    return 0;
}
