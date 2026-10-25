"""Audio diagnostic actions must use valid label text and correct action IDs."""
import unittest
import test_switch_upgrade as switches
class AudioPageTests(unittest.TestCase):
    run_c=switches.SwitchUpgradeTests.run_c
    def test_idle_status_is_not_redrawn_and_only_changed_line_is_invalidated(self):
        self.run_c(r'''
#include <assert.h>
#include <string.h>
#define TX15_AUDIO 1
#include "common.h"
#include "gui/gui.h"
#include "config/display.h"
#include "hardware/tx15/board/audio.h"
struct display_settings Display;
volatile struct tx15_audio_report tx15_audio_report;
static guiObject_t *rows[6];static unsigned count,redraws,mask,ms;
u32 CLOCK_getms(void){return ms;}
u8 PAGE_SetModal(u8 m){return m;}
void PAGE_ShowHeader(const char *s){(void)s;}
void _GUI_Redraw(guiObject_t *o){
    redraws++;for(unsigned i=0;i<count;i++)if(rows[i]==o)mask|=1u<<i;
}
int tx15_audio_hw_test(unsigned now){(void)now;return 1;}
void tx15_audio_hw_stop(void){}
void tx15_audio_hw_volume(unsigned v){tx15_audio_report.volume=v;}
guiObject_t *GUI_CreateLabelBox(guiLabel_t *o,u16 x,u16 y,u16 w,u16 h,const struct LabelDesc *d,
 const char *(*name)(guiObject_t *,const void *),void (*cb)(guiObject_t *,s8,const void *),const void *data){
 (void)x;(void)y;(void)w;(void)h;(void)d;(void)name;(void)data;
 if(!cb){assert(count<6);rows[count++]=(guiObject_t *)o;}
 return (guiObject_t *)o;
}
#include "src/pages/320x240x16/audio_test_page.c"
int main(void){
 PAGE_AudioTestInit(0);redraws=mask=0;
 for(ms=200;ms<=2000;ms+=200)PAGE_AudioTestEvent();
 assert(!redraws);assert(count==6);
 tx15_audio_report.dma_irqs=7;ms+=200;PAGE_AudioTestEvent();
 assert(redraws==1 && mask==2);
 redraws=mask=0;ms+=200;PAGE_AudioTestEvent();assert(!redraws);
 tx15_audio_report.reason=6;tx15_audio_report.last_reg=122;
 ms+=200;PAGE_AudioTestEvent();assert(redraws==2 && mask==5);
 return 0;
}''',[])
    def test_action_names_dispatch_and_exit_stops_audio(self):
        self.run_c(r'''
#include <assert.h>
#include <string.h>
#define TX15_AUDIO 1
#include "common.h"
#include "gui/gui.h"
#include "config/display.h"
#include "hardware/tx15/board/audio.h"
struct display_settings Display;
volatile struct tx15_audio_report tx15_audio_report;
static unsigned actions,played,stopped;
static void (*press_[4])(guiObject_t *,s8,const void *);
static const void *data_[4];
u32 CLOCK_getms(void){return 10;}
u8 PAGE_SetModal(u8 m){return m;}
void PAGE_ShowHeader(const char *s){assert(strstr(s,"AUD4"));}
void _GUI_Redraw(guiObject_t *o){(void)o;}
int tx15_audio_hw_test(unsigned now){assert(now==10);played++;return 1;}
void tx15_audio_hw_stop(void){stopped++;}
void tx15_audio_hw_volume(unsigned v){assert(v<=5);tx15_audio_report.volume=v;}
guiObject_t *GUI_CreateLabelBox(guiLabel_t *o,u16 x,u16 y,u16 w,u16 h,const struct LabelDesc *d,
 const char *(*name)(guiObject_t *,const void *),void (*cb)(guiObject_t *,s8,const void *),const void *data){
 (void)x;(void)y;(void)w;(void)h;(void)d;
 assert(name);const char *text=name((guiObject_t *)o,data);assert(text && *text);
 if(cb){assert((uintptr_t)data<4);press_[actions]=cb;data_[actions++]=data;}
 return (guiObject_t *)o;
}
#include "src/pages/320x240x16/audio_test_page.c"
int main(void){
 tx15_audio_report.volume=3;PAGE_AudioTestInit(0);assert(actions==4);
 tx15_audio_report.reason=TX15_AUDIO_WRITE;tx15_audio_report.last_reg=122;
 assert(strstr(report(NULL,NULL),"Reason:6") && strstr(report(NULL,NULL),"Reg:122"));
 for(unsigned i=0;i<4;i++)press_[i](NULL,0,data_[i]);assert(!played && !stopped);
 press_[0](NULL,-1,data_[0]);assert(played==1);
 press_[1](NULL,-1,data_[1]);assert(stopped==1);
 press_[2](NULL,-1,data_[2]);assert(tx15_audio_report.volume==2);
 press_[3](NULL,-1,data_[3]);assert(tx15_audio_report.volume==3);
 PAGE_AudioTestExit();assert(stopped==2);return 0;
}''',[])
