/* Keep catalog, decoded position and electrical contacts distinguishable.
 * No configuration or peripheral writes; GPL-3.0-or-later. */
#include "common.h"
#include "config/tx.h"
#include "input_monitor.h"
#include "../../../../../hardware/tx15/board/controls.h"
static void position(char *out,unsigned group) {
    out[0]=(tx15_controls.valid&(1u<<group)) && tx15_controls.position[group]<3
        ? '0'+tx15_controls.position[group] : '-';
    out[1]=0;
}
const char *tx15_input_monitor_text(void) {
    static char text[96];char e[2],f[2];position(e,4);position(f,5);
    snprintf(text,sizeof(text),TX15_SWITCH_BUILD " SE:%s/%d SF:%s/%d MASK:%08lX\n74:%04X 75:%04X",
        e,INPUT_NumSwitchPos(INP_SWE0),f,INPUT_NumSwitchPos(INP_SWF0),
        (unsigned long)Transmitter.ignore_src,
        (unsigned)tx15_controls_raw[0],(unsigned)tx15_controls_raw[1]);
    return text;
}
int tx15_input_monitor_changed(void) {
    static unsigned previous[6],initialized;
    const unsigned current[]={tx15_controls_raw[0],tx15_controls_raw[1],tx15_controls.valid,
        tx15_controls.position[4],tx15_controls.position[5],Transmitter.ignore_src};
    if(initialized && !memcmp(current,previous,sizeof(previous)))return 0;
    memcpy(previous,current,sizeof(previous));initialized=1;return 1;
}
