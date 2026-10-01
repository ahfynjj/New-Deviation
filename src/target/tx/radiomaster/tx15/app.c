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
#include "../../../../../hardware/tx15/board/analog.h"
const char DeviationVersion[33]="New Deviation TX15 RAM";
void tx15_app_main(void) {
    CONFIG_LoadTx(); CONFIG_ReadDisplay(); CONFIG_ReadModel(1);
    Model.protocol=PROTOCOL_NONE;
    tx15_analog_init();
    LCD_SetFont(DEFAULT_FONT.font); LCD_SetFontColor(DEFAULT_FONT.font_color);
    GUI_HandleButtons(1); MIXER_Init(); PAGE_Init(); PAGE_ChangeByID(PAGEID_MAIN,0);
    GUI_DrawScreen();
    ((volatile u32 *)0x2400e000u)[2]=3;
    u32 previous=0;
    for(;;) {
        u32 now=CLOCK_getms();
        if(now-previous>=5) {
            previous=now; ((volatile u32 *)0x2400e000u)[12]++; BUTTON_Handler(); tx15_analog_sample(); MIXER_CalcChannels(); PAGE_Event(); GUI_RefreshScreen();
        }
    }
}
