/* New Deviation native TX15 cold-start preparation; GPL-3.0-or-later. */
#ifndef TX15_COLD_START_H
#define TX15_COLD_START_H
#include "../board/clock.h"
/* Call after early_supply.S has finalized LDO and ACTVOSRDY and startup has
 * initialized RAM. Reset HSI64, cache/MPU off; PH12 already held.
 * Establishes VOS1 and Flash read latency before HSE48/PLL128.
 * Never programs Flash cells/options, never disables an external supply.
 * Poll budget is per stage, not milliseconds. Stop on every non-OK result.
 */
enum tx15_clock_result tx15_boot_clock_init(uint32_t budget);
/* Reset-entry-only assembly leaf. No stack/RAM accesses; PH12 + LDO setup.
 * Returns 0, BAD_STATE=1 or SUPPLY_TIMEOUT=5. On failure the reset caller
 * must spin without touching RAM or calling C. IRQs remain disabled. */
enum tx15_clock_result tx15_boot_supply_early(void);
#endif
