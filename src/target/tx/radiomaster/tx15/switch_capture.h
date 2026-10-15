/* Physical switch transition filter; GPL-3.0-or-later. */
#ifndef TX15_SWITCH_CAPTURE_H
#define TX15_SWITCH_CAPTURE_H
#include "../../../../../hardware/tx15/board/controls.h"
struct tx15_switch_capture {unsigned armed,seen;uint8_t previous[6];};
/* 0=no new unambiguous transition, otherwise 1+group*3+position. */
int tx15_switch_capture_step(struct tx15_switch_capture *,const struct tx15_controls *,int armed);
#endif
