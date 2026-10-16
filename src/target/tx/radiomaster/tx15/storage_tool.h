/* Manual read-only internal storage diagnostic; GPL-3.0-or-later. */
#ifndef TX15_STORAGE_TOOL_H
#define TX15_STORAGE_TOOL_H
#include "../../../../../src/storage/card.h"
void tx15_storage_scan(unsigned now);
void tx15_storage_poll(unsigned now);
void tx15_storage_stop(void);
const struct nd_card_report *tx15_storage_report(void);
#endif
