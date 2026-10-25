/* A0 native speaker diagnostic. No storage, model or automatic event changes. */
#ifdef TX15_AUDIO
#include "common.h"
#include "pages.h"
#include "gui/gui.h"
#include "config/display.h"
#include "../../../hardware/tx15/board/audio.h"
static guiLabel_t status[6],play,stop,quieter,louder;
static unsigned refreshed;
static char text[320];
static char lines[6][96];
static const char *action_name(guiObject_t *obj,const void *data) {
    (void)obj;
    static const char *const names[]={"Play 300 ms","Stop","Volume -","Volume +"};
    uintptr_t id=(uintptr_t)data;return id<4?names[id]:"";
}
static const char *report(guiObject_t *obj,const void *data) {
    (void)obj;(void)data;
    static const char *const names[]={"Off","Starting","Configuring","Ready","Error"};
    unsigned s=tx15_audio_report.state;
    snprintf(text,sizeof(text),"%s Reason:%u   Volume:%u/5\nTests:%u DMA:%u Errors:%u U:%u\nStep:%u Reg:%u Value:%02X\nI2C:%08X\nDmaFlags:%08X SPI:%08X\nInit:%ums Gap:%ums",
        s<5?names[s]:"Error",(unsigned)tx15_audio_report.reason,(unsigned)tx15_audio_report.volume,
        (unsigned)tx15_audio_report.tests,(unsigned)tx15_audio_report.dma_irqs,
        (unsigned)tx15_audio_report.errors,(unsigned)tx15_audio_report.underruns,
        (unsigned)tx15_audio_report.steps,(unsigned)tx15_audio_report.last_reg,(unsigned)tx15_audio_report.last_value,
        (unsigned)tx15_audio_report.i2c_status,(unsigned)tx15_audio_report.dma_flags,(unsigned)tx15_audio_report.spi_status,
        (unsigned)tx15_audio_report.elapsed,(unsigned)tx15_audio_report.max_gap);
    return text;
}
static const char *status_line(guiObject_t *obj,const void *data) {
    (void)obj;uintptr_t row=(uintptr_t)data;return row<6?lines[row]:"";
}
static void update_status(unsigned redraw) {
    const char *p=report(NULL,NULL);
    for(unsigned row=0;row<6;row++) {
        char next[96];unsigned n=0;
        while(*p && *p!='\n') {if(n<sizeof(next)-1)next[n++]=*p;p++;}
        next[n]=0;if(*p=='\n')p++;
        if(strcmp(lines[row],next)) {
            strcpy(lines[row],next);
            if(redraw)GUI_Redraw((guiObject_t *)&status[row]);
        }
    }
}
static void action(guiObject_t *obj,s8 press,const void *data) {
    (void)obj;if(press!=-1)return;
    uintptr_t id=(uintptr_t)data;unsigned v=tx15_audio_report.volume;
    if(id==0)(void)tx15_audio_hw_test(CLOCK_getms());
    else if(id==1)tx15_audio_hw_stop();
    else if(id==2)tx15_audio_hw_volume(v?v-1:0);
    else tx15_audio_hw_volume(v<5?v+1:5);
    update_status(1);
}
void PAGE_AudioTestInit(int page) {
    (void)page;PAGE_SetModal(0);PAGE_ShowHeader("Audio test AUD4");
    memset(lines,0,sizeof(lines));update_status(0);
    for(unsigned row=0;row<6;row++)
        GUI_CreateLabelBox(&status[row],20,44+row*24,440,23,&LABEL_FONT,status_line,NULL,(const void *)(uintptr_t)row);
    GUI_CreateLabelBox(&play,20,210,210,36,&MENU_FONT,action_name,action,NULL);
    GUI_CreateLabelBox(&stop,250,210,210,36,&MENU_FONT,action_name,action,(const void *)1);
    GUI_CreateLabelBox(&quieter,20,266,210,36,&MENU_FONT,action_name,action,(const void *)2);
    GUI_CreateLabelBox(&louder,250,266,210,36,&MENU_FONT,action_name,action,(const void *)3);
    refreshed=CLOCK_getms();
}
void PAGE_AudioTestEvent(void) {
    unsigned now=CLOCK_getms();if(now-refreshed<200)return;
    refreshed=now;update_status(1);
}
void PAGE_AudioTestExit(void) {tx15_audio_hw_stop();}
#endif
