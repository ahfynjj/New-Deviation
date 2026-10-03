/* Bounded native payload transaction; GPL-3.0-or-later. */
#ifndef TX15_BOOT_LOADER_H
#define TX15_BOOT_LOADER_H
#include "image.h"
#define TX15_BOOT_MAX_BYTES (64u+0x6c000u+0x80000u)
#define TX15_BOOT_SLOT_OFFSET 0u
#define TX15_BOOT_SLOT_BYTES 0x100000u
#define TX15_BOOT_STAGING 0xd0100000u
enum tx15_boot_load_result { TX15_BOOT_LOAD_OK,TX15_BOOT_LOAD_BAD_ARGUMENT,
    TX15_BOOT_LOAD_READ_ERROR,TX15_BOOT_LOAD_BAD_IMAGE,TX15_BOOT_LOAD_COPY_ERROR,
    TX15_BOOT_LOAD_VERIFY_ERROR };
struct tx15_boot_io {
    void *context;
    /* Return nonzero only for a complete transfer. No persistent writes. */
    int (*read)(void *,uint32_t offset,uint8_t *destination,uint32_t bytes);
    int (*copy)(void *,const struct tx15_boot_segment *);
    int (*verify)(void *,const struct tx15_boot_segment *);
};
/* Stage all source bytes and validate everything before the first copy.
 * Staging is caller-owned, separate from destination RAM and immutable during
 * validation/copy/verification. Entry remains zero on every failure; caller
 * must never jump after a partial copy. This API never executes an entry. */
enum tx15_boot_load_result tx15_boot_load(const struct tx15_boot_io *,
    uint32_t slot_offset,uint32_t slot_bytes,uint8_t *staging,uint32_t capacity,uint32_t *entry);
#endif
