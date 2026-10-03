/* New Deviation native TX15 read-only SPI NOR bootstrap; GPL-3.0-or-later. */
#ifndef TX15_BOOT_QSPI_H
#define TX15_BOOT_QSPI_H
#include <stdint.h>
enum tx15_qspi_result { TX15_QSPI_OK,TX15_QSPI_BAD_STATE,TX15_QSPI_TIMEOUT,
    TX15_QSPI_TRANSFER_ERROR,TX15_QSPI_BAD_ID };
/* Reset-idle controller only, after confirmed PLL128/HCLK64 initialization.
 * Configures 4 MHz single-line SPI; emits only 0x9f JEDEC and 0x03 read.
 * No program/erase/WREN/status-write/reset-chip/quad-enable commands.
 * Identity is an observation, not automatic approval of capacity/installation.
 */
enum tx15_qspi_result tx15_boot_qspi_init(uint32_t *jedec_id,uint32_t poll_budget);
/* Raw first-16MiB address window. Actual NOR identity/capacity/protocol must be
 * verified by the installer before trusting data or choosing a Flash layout.
 * On failure the destination may be partial; caller must discard it.
 */
enum tx15_qspi_result tx15_boot_qspi_read(uint32_t offset,uint8_t *destination,uint32_t bytes,uint32_t poll_budget);
/* Reset only this owned controller and disable its clock; preserve FMC and
 * other RCC bits. GPIO restore belongs to the enclosing RAM bench session. */
void tx15_boot_qspi_stop(void);
#endif
