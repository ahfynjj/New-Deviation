#include "boot_contract.h"
#include "../../../../../hardware/tx15/boot/handoff.h"
int tx15_app_boot_accept(volatile struct probe_report *r) {
#ifdef TX15_STANDALONE
    if(!tx15_boot_handoff_valid(r))return 0;
    r->version=10;
#else
    if(!r || r->magic!=PROBE_MAGIC || r->version!=6 || r->state!=PROBE_RUNNING || r->error)return 0;
    r->version=7;
#endif
    r->state=PROBE_INIT;r->loops=0;return 1;
}
