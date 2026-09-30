/* Read-only embedded Deviation resources; GPL-3.0-or-later. */
#ifndef TX15_ROMFS_H
#define TX15_ROMFS_H
#include <stddef.h>
#include <stdint.h>
struct tx15_resource { const char *path; const uint8_t *data; size_t size; };
extern const struct tx15_resource tx15_resources[];
extern const size_t tx15_resource_count;
#endif
