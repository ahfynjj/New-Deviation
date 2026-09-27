/* New Deviation TX15 MAX board support; GPL-3.0-or-later. */
#ifndef NEW_DEVIATION_TX15_POWER_H
#define NEW_DEVIATION_TX15_POWER_H
#include <stdint.h>

enum tx15_power_bits {
    TX15_HOLD_OUTPUT = 1u,
    TX15_HOLD_LATCH_HIGH = 2u,
    TX15_HOLD_PIN_HIGH = 4u,
    TX15_BUTTON_INPUT = 8u,
    TX15_BUTTON_PRESSED = 16u
};
#define TX15_POWER_READY 15u

/* Caller must have verified TX15 hardware. PH12 is active high; PA4 active low.
 * Preserve every unrelated pin. No shutdown or RF power control is performed.
 */
void tx15_power_init(void);
uint32_t tx15_power_status(void);
#endif
