/* Restricted external application transaction; GPL-3.0-or-later. */
#ifndef TX15_UPDATE_TRANSACTION_H
#define TX15_UPDATE_TRANSACTION_H
#include "receiver.h"
struct tx15_update_flash_info {
    uint32_t jedec,capacity,page_bytes,erase_bytes;
    uint8_t sr1,sr2,sr3,sfdp_valid;
};
struct tx15_update_io {
    void *ctx;
    int (*observe)(void*,struct tx15_update_flash_info*);
    int (*read)(void*,uint32_t,uint8_t*,size_t);
    int (*erase4k)(void*,uint32_t);
    int (*program)(void*,uint32_t,const uint8_t*,size_t);
    void (*service)(void*);
};
struct tx15_update_tx {
    struct tx15_update_io io;
    struct tx15_update_package package;
    uint8_t *shadow;
    uint32_t erase_bytes,offset;
    unsigned active,stepping,header_pending;
    struct tx15_update_reply status;
};
int tx15_update_flash_writable(const struct tx15_update_flash_info*);
int tx15_update_tx_prepare(struct tx15_update_tx*,const struct tx15_update_io*,
                           const struct tx15_update_package*,uint8_t*,size_t);
int tx15_update_tx_step(struct tx15_update_tx*);
#endif
