/* Read-only 512-byte sector geometry inspection. GPL-3.0-or-later. */
#ifndef ND_STORAGE_VOLUME_H
#define ND_STORAGE_VOLUME_H
#include <stdint.h>
enum {ND_VOLUME_SUPER=1,ND_VOLUME_MBR=2,ND_VOLUME_GPT=3};
enum {ND_FS_NONE,ND_FS_FAT12,ND_FS_FAT16,ND_FS_FAT32,ND_FS_EXFAT};
struct nd_volume {
    unsigned fs,cluster_blocks;
    uint32_t lba,blocks,data_lba,clusters,root_cluster;
};
/* Selects the first supported MBR data partition, or a superfloppy.
 * GPT is reported without following it. No mount/read/write operation. */
int nd_volume_partition(const uint8_t sector[512],uint64_t media_blocks,uint32_t *lba,uint64_t *span);
int nd_volume_decode(const uint8_t sector[512],uint32_t lba,uint64_t span,uint64_t media_blocks,struct nd_volume *);
#endif
