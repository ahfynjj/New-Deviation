/* Bounded, observation-only SFDP policy; GPL-3.0-or-later. */
#ifndef TX15_UPDATE_NOR_GEOMETRY_H
#define TX15_UPDATE_NOR_GEOMETRY_H
#include "transaction.h"
int tx15_update_nor_assess(uint32_t jedec,const uint8_t status[3],
                           const uint8_t *sfdp,size_t bytes,
                           struct tx15_update_flash_info *out);
#endif
