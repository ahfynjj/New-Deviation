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
#ifdef TX15_ELRS_RC
#include "rf_model.h"
#include "rf_lua.h"
static unsigned lua_requested;
void tx15_request_lua_for(unsigned slot) {if(slot<2)lua_requested=slot+1;}
#endif
#include "../../../../../hardware/tx15/board/analog.h"
#include "../../../../../hardware/tx15/board/battery.h"
#include "../../../../../hardware/tx15/board/controls.h"
#ifdef TX15_STANDALONE
const char DeviationVersion[33]="New Deviation TX15";
#else
const char DeviationVersion[33]="New Deviation TX15 RAM";
#endif
#ifdef TX15_ELRS_LUA
void tx15_lua_tool(void);
#endif
void tx15_app_main(void) {
    CONFIG_LoadTx(); CONFIG_ReadDisplay(); CONFIG_ReadModel(1);
#ifndef TX15_ELRS_RC
    Model.protocol=PROTOCOL_NONE;
#endif
    tx15_analog_init();
#ifdef TX15_STANDALONE
    tx15_battery_init();
#endif
    tx15_controls_init();
    LCD_SetFont(DEFAULT_FONT.font); LCD_SetFontColor(DEFAULT_FONT.font_color);
    GUI_HandleButtons(1); MIXER_Init(); PAGE_Init(); PAGE_ChangeByID(PAGEID_MAIN,0);
    GUI_DrawScreen();
#ifdef TX15_ELRS_RC
    tx15_rf_model_start(CLOCK_getms());
#endif
#ifdef TX15_ELRS_DISCOVERY
    tx15_rf_discovery_init(CLOCK_getms());
#endif
    ((volatile u32 *)0x2400e000u)[2]=3;
#if defined(TX15_ELRS_LUA) && !defined(TX15_ELRS_RC)
    tx15_lua_tool();
#endif
    u32 previous=0;
    for(;;) {
        CLOCK_ResetWatchdog();
        u32 now=CLOCK_getms();
        if(now-previous>=5) {
            previous=now; BUTTON_Handler();
#ifndef TX15_ELRS_RC
            MIXER_CalcChannels();
#else
            if(lua_requested) {
                unsigned slot=lua_requested-1;lua_requested=0;
                if(tx15_rf_lua_select(slot)->slot==(int)slot)tx15_lua_tool();
            }
#endif
            PAGE_Event(); GUI_RefreshScreen();
        }
    }
}
