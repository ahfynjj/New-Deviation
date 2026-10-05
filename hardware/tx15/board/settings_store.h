/* Two-copy committed records. Callbacks use offsets within a 64KiB region. */
#ifndef TX15_SETTINGS_STORE_H
#define TX15_SETTINGS_STORE_H
#include <stdint.h>
#define TX15_STORE_SLOT_BYTES 32768u
#define TX15_STORE_MAX_BYTES (TX15_STORE_SLOT_BYTES-32u)
struct tx15_store_io {
 void *ctx;
 int (*read)(void *,unsigned,void *,unsigned);
 int (*erase)(void *,unsigned);
 int (*program)(void *,unsigned,const void *,unsigned);
};
int tx15_store_load(const struct tx15_store_io *,unsigned id,void *,unsigned bytes);
int tx15_store_save(const struct tx15_store_io *,unsigned id,const void *,unsigned bytes);
#endif
