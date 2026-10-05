/* Native Deviation menu entry; Lua runs outside page creation callbacks. */
#ifdef TX15_ELRS_RC
#include "common.h"
#include "pages.h"
#include "gui/gui.h"
#include "config/model.h"
#include "config/display.h"
#include "target/tx/radiomaster/tx15/elrs_menu.h"
#include "target/tx/radiomaster/tx15/rf_rc.h"
static guiLabel_t targets[2],message;
static const char *target_name(guiObject_t *obj,const void *data) {
 (void)obj;return (long)data ? "External ELRS" : "Internal ELRS";
}
static void choose(guiObject_t *obj,s8 press,const void *data) {
    (void)obj;
    if(press!=-1)return;
    unsigned slot=(unsigned)(long)data;
    if(!tx15_module_enabled(&Model.tx15_modules[slot]))return;
    PAGE_Pop();tx15_request_lua_for(slot);
}
void PAGE_ElrsLuaInit(int page) {
    (void)page;
    PAGE_SetModal(0);PAGE_ShowHeader("ELRS Lua");
    unsigned count=0,last=0;
#ifdef TX15_ELRS_PRODUCT
    const unsigned slots=2;
#else
    const unsigned slots=1;
#endif
    for(unsigned slot=0;slot<slots;slot++) if(tx15_module_enabled(&Model.tx15_modules[slot])) {count++;last=slot;}
    if(count==1) {PAGE_Pop();tx15_request_lua_for(last);return;}
    if(!count) {
        GUI_CreateLabelBox(&message,20,90,440,40,&LABEL_FONT,NULL,NULL,"Enable RF in Model setup");return;
    }
    GUI_CreateLabelBox(&targets[0],20,90,440,30,&MENU_FONT,target_name,choose,NULL);
    GUI_CreateLabelBox(&targets[1],20,135,440,30,&MENU_FONT,target_name,choose,(const void *)1);
    GUI_SetSelected((guiObject_t *)&targets[0]);
}
#endif
