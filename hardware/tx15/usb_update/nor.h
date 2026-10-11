/* Restricted native 4MHz single-line NOR backend; GPL-3.0-or-later. */
#ifndef TX15_UPDATE_NOR_H
#define TX15_UPDATE_NOR_H
#include "transaction.h"
struct tx15_update_nor {
    void (*service)(void*);
    uint32_t (*ms)(void*);
    void *ctx;
    uint32_t budget;
    unsigned ready,active;
};
/* Requires the already-owned controller from tx15_boot_qspi_init. */
int tx15_update_nor_init(struct tx15_update_nor*,void(*)(void*),uint32_t(*)(void*),void*,uint32_t);
int tx15_update_nor_observe(void*,struct tx15_update_flash_info*);
int tx15_update_nor_read(void*,uint32_t,uint8_t*,size_t);
int tx15_update_nor_erase4k(void*,uint32_t);
int tx15_update_nor_program(void*,uint32_t,const uint8_t*,size_t);
#endif
