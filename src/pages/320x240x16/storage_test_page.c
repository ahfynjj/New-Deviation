/* S0 manual read-only SDMMC1 metadata probe. GPL-3.0-or-later. */
#ifdef TX15_STORAGE
#include "common.h"
#include "pages.h"
#include "gui/gui.h"
#include "config/display.h"
#include "storage_tool.h"
#include "../../../hardware/tx15/board/storage.h"
static guiLabel_t status,scan,cancel;
static unsigned refreshed;
static char text[256];
static const char *action_name(guiObject_t *obj,const void *data) {
    (void)obj;return data?"Stop":"Scan (read only)";
}
static const char *report(guiObject_t *obj,const void *data) {
    (void)obj;(void)data;
    static const char *const states[]={"Off - select Scan","Scanning","Ready (metadata only)","Error"};
    static const char *const fs[]={"Unknown","FAT12","FAT16","FAT32","exFAT (unsupported)"};
    const struct nd_card_report *r=tx15_storage_report();
    const char *format=r->partition_kind==ND_VOLUME_GPT?"GPT (unsupported)":r->volume.fs<5?fs[r->volume.fs]:"Unknown";
    snprintf(text,sizeof(text),"%s   Error:%u HW:%u\n%u MiB   %s   RCA:%04X\n%s   LBA:%u\nCMD:%u   STA:%08X\nRESP:%08X   Reads:%u\nNo writes / no model migration",
        r->state<4?states[r->state]:"Error",r->error,(unsigned)tx15_storage_hw_report.reason,
        (unsigned)(r->blocks/2048),r->high_capacity?"SDHC/SDXC":"SDSC",(unsigned)r->rca,
        format,(unsigned)r->volume.lba,r->last_command,(unsigned)tx15_storage_hw_report.status,
        (unsigned)tx15_storage_hw_report.response,(unsigned)tx15_storage_hw_report.reads);
    return text;
}
static void action(guiObject_t *obj,s8 press,const void *data) {
    (void)obj;if(press!=-1)return;
    if(data)tx15_storage_stop();else tx15_storage_scan(CLOCK_getms());
    GUI_Redraw((guiObject_t *)&status);
}
void PAGE_StorageTestInit(int page) {
    (void)page;PAGE_SetModal(0);PAGE_ShowHeader("Storage test STO0");
    GUI_CreateLabelBox(&status,20,44,440,174,&LABEL_FONT,report,NULL,NULL);
    GUI_CreateLabelBox(&scan,20,240,210,36,&MENU_FONT,action_name,action,NULL);
    GUI_CreateLabelBox(&cancel,250,240,210,36,&MENU_FONT,action_name,action,(const void *)1);
    refreshed=CLOCK_getms();
}
void PAGE_StorageTestEvent(void) {
    unsigned now=CLOCK_getms();if(now-refreshed<200)return;
    refreshed=now;GUI_Redraw((guiObject_t *)&status);
}
void PAGE_StorageTestExit(void) {tx15_storage_stop();}
#endif
