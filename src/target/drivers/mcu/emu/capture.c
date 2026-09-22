#include "common.h"
#include "pages.h"
#include "config/model.h"
#include "capture.h"

int EMU_PrepareCapturePage(const char *page)
{
    if (!page || strcmp(page, "main") == 0)
        return 1;
#if LCD_DEPTH == 16
    if (strcmp(page, "mixer") == 0) {
        Model.mixer_mode = MIXER_ADVANCED;
        PAGE_ChangeByID(PAGEID_MIXER, 0);
#if HAS_STANDARD_GUI
    } else if (strcmp(page, "curve") == 0) {
        CONFIG_ResetModel();
        if (!CONFIG_ReadTemplate("heli_std.ini"))
            return 0;
        STDMIXER_Preset();
        PAGE_ChangeByID(PAGEID_THROCURVES, 0);
#endif
    } else {
        return 0;
    }
    GUI_RefreshScreen();
    return 1;
#else
    return 0;
#endif
}
