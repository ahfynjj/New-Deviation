/* New Deviation TX15 read-only installation prerequisites; GPL-3.0-or-later. */
#ifndef TX15_FLASH_INFO_H
#define TX15_FLASH_INFO_H
#include "qspi.h"
#define TX15_SFDP_CAPTURE_BYTES 1024u
struct tx15_flash_info {
    uint8_t status[3],reserved;
    uint8_t sfdp[TX15_SFDP_CAPTURE_BYTES];
};
/* Requires the already-owned 4MHz single-line controller from qspi_init.
 * Only RDSR 05/35/15 and RDSFDP 5A; no WREN or persistent configuration.
 * On any failure caller discards the entire record and resets the controller.
 */
enum tx15_qspi_result tx15_flash_info_read(uint32_t jedec,
    struct tx15_flash_info *info,uint32_t budget);
#endif
