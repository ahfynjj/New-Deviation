#ifdef TX15_STORAGE
#include "storage_tool.h"
#include "../../../../../hardware/tx15/board/storage.h"
static struct nd_card card;
void tx15_storage_scan(unsigned now) {nd_card_begin(&card,&tx15_storage_ops,0,now);}
void tx15_storage_poll(unsigned now) {nd_card_poll(&card,now);}
void tx15_storage_stop(void) {nd_card_stop(&card);}
const struct nd_card_report *tx15_storage_report(void) {return &card.report;}
#endif
