/* A0 native speaker diagnostic. No storage, model or automatic event changes. */
#ifdef TX15_AUDIO
#include "common.h"
#include "pages.h"
#include "gui/gui.h"
#include "config/display.h"
#include "../../../hardware/tx15/board/audio.h"
static guiLabel_t status,play,stop,quieter,louder;
static unsigned refreshed;
static char text[144];
static const char *action_name(guiObject_t *obj,const void *data) {
    (void)obj;
    static const char *const names[]={"Play 300 ms","Stop","Volume -","Volume +"};
    uintptr_t id=(uintptr_t)data;return id<4?names[id]:"";
}
static const char *report(guiObject_t *obj,const void *data) {
    (void)obj;(void)data;
    static const char *const names[]={"Off","Starting","Configuring","Ready","Error"};
    unsigned s=tx15_audio_report.state;
    snprintf(text,sizeof(text),"%s   Volume: %u/5\nTests: %u   DMA: %u\nErrors: %u   Underruns: %u",
        s<5?names[s]:"Error",(unsigned)tx15_audio_report.volume,(unsigned)tx15_audio_report.tests,
        (unsigned)tx15_audio_report.dma_irqs,(unsigned)tx15_audio_report.errors,(unsigned)tx15_audio_report.underruns);
    return text;
}
static void action(guiObject_t *obj,s8 press,const void *data) {
    (void)obj;if(press!=-1)return;
    uintptr_t id=(uintptr_t)data;unsigned v=tx15_audio_report.volume;
    if(id==0)(void)tx15_audio_hw_test(CLOCK_getms());
    else if(id==1)tx15_audio_hw_stop();
    else if(id==2)tx15_audio_hw_volume(v?v-1:0);
    else tx15_audio_hw_volume(v<5?v+1:5);
    GUI_Redraw((guiObject_t *)&status);
}
void PAGE_AudioTestInit(int page) {
    (void)page;PAGE_SetModal(0);PAGE_ShowHeader("Audio test AUD0");
    GUI_CreateLabelBox(&status,20,48,440,90,&LABEL_FONT,report,NULL,NULL);
    GUI_CreateLabelBox(&play,20,150,210,36,&MENU_FONT,action_name,action,NULL);
    GUI_CreateLabelBox(&stop,250,150,210,36,&MENU_FONT,action_name,action,(const void *)1);
    GUI_CreateLabelBox(&quieter,20,210,210,36,&MENU_FONT,action_name,action,(const void *)2);
    GUI_CreateLabelBox(&louder,250,210,210,36,&MENU_FONT,action_name,action,(const void *)3);
    refreshed=CLOCK_getms();
}
void PAGE_AudioTestEvent(void) {
    unsigned now=CLOCK_getms();if(now-refreshed<200)return;
    refreshed=now;GUI_Redraw((guiObject_t *)&status);
}
void PAGE_AudioTestExit(void) {tx15_audio_hw_stop();}
#endif
