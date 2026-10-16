"""Storage is never scanned on entry; only the explicit read-only action starts it."""
import unittest
import test_switch_upgrade as switches

class StoragePageTests(unittest.TestCase):
    run_c=switches.SwitchUpgradeTests.run_c
    def test_manual_scan_cancel_and_metadata(self):
        self.run_c(r'''
#include <assert.h>
#include <string.h>
#define TX15_STORAGE 1
#include "common.h"
#include "gui/gui.h"
#include "config/display.h"
#include "src/target/tx/radiomaster/tx15/storage_tool.h"
#include "hardware/tx15/board/storage.h"
struct display_settings Display;
volatile struct tx15_storage_hw_report tx15_storage_hw_report;
static struct nd_card_report card_report;
static unsigned scanned,stopped,actions,redraws,now=10;
static void (*press_[2])(guiObject_t *,s8,const void *);
static const void *data_[2];
u32 CLOCK_getms(void){return now;}
u8 PAGE_SetModal(u8 m){return m;}
void PAGE_ShowHeader(const char *s){assert(strstr(s,"STO0"));}
void _GUI_Redraw(guiObject_t *o){(void)o;redraws++;}
void tx15_storage_scan(unsigned n){assert(n==now);scanned++;}
void tx15_storage_stop(void){stopped++;}
const struct nd_card_report *tx15_storage_report(void){return &card_report;}
guiObject_t *GUI_CreateLabelBox(guiLabel_t *o,u16 x,u16 y,u16 w,u16 h,const struct LabelDesc *d,
 const char *(*name)(guiObject_t *,const void *),void (*cb)(guiObject_t *,s8,const void *),const void *data){
 (void)x;(void)y;(void)w;(void)h;(void)d;assert(name && *name((guiObject_t *)o,data));
 if(cb){assert(actions<2);press_[actions]=cb;data_[actions++]=data;}
 return (guiObject_t *)o;
}
#include "src/pages/320x240x16/storage_test_page.c"
int main(void){
 PAGE_StorageTestInit(0);assert(actions==2 && !scanned && !stopped);
 press_[0](NULL,0,data_[0]);assert(!scanned);
 press_[0](NULL,-1,data_[0]);assert(scanned==1);
 press_[1](NULL,-1,data_[1]);assert(stopped==1);
 unsigned previous=redraws;PAGE_StorageTestEvent();assert(previous==redraws);
 now+=200;PAGE_StorageTestEvent();assert(redraws==previous+1);
 card_report.state=ND_CARD_READY;card_report.blocks=33554432;card_report.high_capacity=1;
 card_report.volume.fs=ND_FS_FAT32;
 assert(strstr(report(NULL,NULL),"16384 MiB") && strstr(report(NULL,NULL),"FAT32"));
 PAGE_StorageTestExit();assert(stopped==2);return 0;
}''',[])
