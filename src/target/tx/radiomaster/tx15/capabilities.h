/* Native MAX has six three-position switches. Keep the old catalog available
 * only for offline persistence-layout regression fixtures. */
#ifndef TX15_LEGACY_INPUT_LAYOUT
#define TX15_NATIVE_3POS 1
#endif
#include "../emu_tx15/capabilities.h"
#undef TX15_NATIVE_3POS
