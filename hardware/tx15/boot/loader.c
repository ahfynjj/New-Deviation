#include "loader.h"
enum tx15_boot_load_result tx15_boot_load(const struct tx15_boot_io *io,
    uint32_t start,uint32_t slot,uint8_t *staging,uint32_t capacity,uint32_t *entry)
{
    if (entry) *entry=0;
    if (!entry || !io || !io->read || !io->copy || !io->verify || !staging || capacity<64
            || slot<64 || slot>TX15_BOOT_SLOT_BYTES || start>0x1000000u-slot)
        return TX15_BOOT_LOAD_BAD_ARGUMENT;
    if (!io->read(io->context,start,staging,64)) return TX15_BOOT_LOAD_READ_ERROR;
    uint32_t bytes=tx15_boot_image_size(staging);
    if (!bytes || bytes>slot || bytes>capacity) return TX15_BOOT_LOAD_BAD_IMAGE;
    for (uint32_t at=64;at<bytes;) {
        uint32_t count=bytes-at;if (count>256) count=256;
        if (!io->read(io->context,start+at,staging+at,count)) return TX15_BOOT_LOAD_READ_ERROR;
        at+=count;
    }
    struct tx15_boot_image plan;
    if (!tx15_boot_image_validate(staging,bytes,&plan)) return TX15_BOOT_LOAD_BAD_IMAGE;
    for (unsigned i=0;i<2;i++) {
        if (!io->copy(io->context,&plan.segments[i])) return TX15_BOOT_LOAD_COPY_ERROR;
        if (!io->verify(io->context,&plan.segments[i])) return TX15_BOOT_LOAD_VERIFY_ERROR;
    }
    *entry=plan.entry;return TX15_BOOT_LOAD_OK;
}
