/* Native Deviation TX15 factory input simulation; GPL-3.0-or-later. */
#include "common.h"
#include "target/drivers/mcu/emu/fltk.h"
#include "mixer.h"

static unsigned char positions[7];
static unsigned held;

int EMU_HandleTargetKey(int key, int pressed)
{
    static const char keys[] = "xcvzbn";
    unsigned i;
    if (key >= '1' && key <= '6') {
        if (pressed)
            positions[6] = key - '1';
        return 1;
    }
    for (i = 0; i < 6; i++) {
        if (key != keys[i])
            continue;
        if (!pressed) {
            held &= ~(1u << i);
            if (i == 5)
                positions[i] = 0;
        } else if (!(held & (1u << i))) {
            held |= 1u << i;
            positions[i] = (positions[i] + 1) % (i < 4 ? 3 : 2);
        }
        return 1;
    }
    return 0;
}

void EMU_ReleaseTargetKeys(void)
{
    held = 0;
    positions[5] = 0;
}

s32 ADC_ReadRawInput(int channel)
{
    int value;
    switch (channel) {
    case INP_AILERON: value = gui.aileron; break;
    case INP_ELEVATOR: value = gui.elevator; break;
    case INP_THROTTLE: value = gui.throttle; break;
    case INP_RUDDER: value = gui.rudder; break;
    case INP_S1: value = gui.aux2; break;
    case INP_S2: value = gui.aux3; break;
    default: return 0;
    }
    return CHAN_MIN_VALUE + (CHAN_MAX_VALUE - CHAN_MIN_VALUE) / 10 * value;
}

s32 ADC_NormalizeChannel(int channel)
{
    return ADC_ReadRawInput(channel);
}

s32 SWITCH_ReadRawInput(int channel)
{
    static const int first[] = {
        INP_SWA0, INP_SWB0, INP_SWC0, INP_SWD0, INP_SWE0, INP_SWF0, INP_SW60
    };
    static const int count[] = {3, 3, 3, 3, 2, 2, 6};
    for (unsigned i = 0; i < 7; i++) {
        if (channel >= first[i] && channel < first[i] + count[i])
            return channel - first[i] == positions[i];
    }
    return 0;
}

void CHAN_SetSwitchCfg(const char *str)
{
    (void)str;
}
