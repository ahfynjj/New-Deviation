/* P2 RAM-only integration entry; GPL-3.0-or-later.
 * Called only after board initialization. Not a standalone boot image.
 */
#include "common.h"
#include "gui/gui.h"
#include "pages.h"
#include "buttons.h"
#include "mixer.h"
#include "config/model.h"
#include "config/tx.h"
#include "config/display.h"
#include "rf.h"
#include "../../../../../hardware/tx15/board/analog.h"
const char DeviationVersion[33]="New Deviation TX15 RAM";
#ifdef TX15_ELRS_LUA
void tx15_lua_tool(void);
#endif
void tx15_app_main(void) {
    CONFIG_LoadTx(); CONFIG_ReadDisplay(); CONFIG_ReadModel(1);
    Model.protocol=PROTOCOL_NONE;
    tx15_analog_init();
    LCD_SetFont(DEFAULT_FONT.font); LCD_SetFontColor(DEFAULT_FONT.font_color);
    GUI_HandleButtons(1); MIXER_Init(); PAGE_Init(); PAGE_ChangeByID(PAGEID_MAIN,0);
    GUI_DrawScreen();
#ifdef TX15_ELRS_DISCOVERY
    tx15_rf_discovery_init(CLOCK_getms());
#endif
    ((volatile u32 *)0x2400e000u)[2]=3;
#ifdef TX15_ELRS_LUA
    tx15_lua_tool();
#endif
    u32 previous=0;
    for(;;) {
        CLOCK_ResetWatchdog();
        u32 now=CLOCK_getms();
        if(now-previous>=5) {
            previous=now; BUTTON_Handler(); MIXER_CalcChannels(); PAGE_Event(); GUI_RefreshScreen();
        }
    }
}
