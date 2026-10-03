/* New Deviation native boot payload validation; GPL-3.0-or-later. */
#ifndef TX15_BOOT_IMAGE_H
#define TX15_BOOT_IMAGE_H
#include <stddef.h>
#include <stdint.h>
struct tx15_boot_segment {
    const uint8_t *source;
    uint32_t destination, length;
};
struct tx15_boot_image {
    uint32_t entry;
    struct tx15_boot_segment segments[2];
};
/* Header-only size/descriptor check before a bounded storage read. Does not
 * validate payload CRC/vectors and never authorizes execution. Returns 0 on error. */
uint32_t tx15_boot_image_size(const uint8_t header[64]);
/* Returns 1 only after checking the whole immutable source image. On failure
 * clears the plan. Does not copy, execute, or touch hardware/Flash. CRC detects
 * corruption; it is not an authenticity/signature check. */
int tx15_boot_image_validate(const uint8_t *source, size_t bytes, struct tx15_boot_image *plan);
#endif
