/* New Deviation native USB update package; GPL-3.0-or-later. */
#ifndef TX15_UPDATE_PACKAGE_H
#define TX15_UPDATE_PACKAGE_H
#include "../boot/image.h"
#define TX15_UPDATE_HEADER_BYTES 128u
#define TX15_UPDATE_IMAGE_MAX (64u+0x6c000u+0x80000u)
#define TX15_UPDATE_BOOT_API 1u
#define TX15_UPDATE_SETTINGS_ABI 1u
struct tx15_update_package {
    const uint8_t *image;
    uint32_t image_bytes, image_crc;
    struct tx15_boot_image boot;
};
uint32_t tx15_update_crc(uint32_t crc, const uint8_t *data, size_t bytes);
/* Checks header without authorizing execution; returns bounded ND15 length. */
uint32_t tx15_update_header_validate(const uint8_t *header, uint32_t boot_api, uint32_t settings_abi);
int tx15_update_package_validate(const uint8_t *data, size_t bytes, uint32_t boot_api,
                                 uint32_t settings_abi, struct tx15_update_package *out);
#endif
