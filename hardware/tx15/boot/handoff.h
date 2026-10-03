/* Distinct cold-loader contract; do not fabricate legacy V6 bench evidence. */
#ifndef TX15_BOOT_HANDOFF_H
#define TX15_BOOT_HANDOFF_H
#include "../ram_probe/probe.h"
#define TX15_BOOT_HANDOFF_VERSION 9u
enum { TX15_BOOT_CLOCK=1u,TX15_BOOT_SDRAM=2u,TX15_BOOT_DISPLAY=4u,
       TX15_BOOT_IMAGE=8u,TX15_BOOT_COPIED=16u,TX15_BOOT_READY=31u };
/* V9 uses ram_words for completed-stage flags, not a RAM test word count. */
int tx15_boot_handoff_valid(const volatile struct probe_report *report);
#endif
