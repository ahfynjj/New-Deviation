/* Native mixer switch editing, scoped to explicitly marked fields. */
#ifndef TX15_MIX_SWITCH_H
#define TX15_MIX_SWITCH_H
#include "gui/gui.h"
#include "switch_capture.h"
#define TX15_MIX_SWITCH_BUILD "SRC1"
/* Bits 0/1 retain the existing TextSelect enabled/center-press meanings. */
#define TX15_SWITCH_FIELD 4u
#define TX15_SWITCH_EDITING 8u
#define TX15_SOURCE_FIELD 16u
void tx15_mix_switch_register(guiTextSelect_t *field);
void tx15_mix_source_register(guiTextSelect_t *field);
void tx15_mix_switch_init(void);
void tx15_mix_switch_poll(void);
void tx15_mix_switch_forget(guiObject_t *object);
#endif
