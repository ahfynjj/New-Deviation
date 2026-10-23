"""Actual shutdown modal: exact cancellation restore and continuing services."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[3]
HARNESS=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
static uint16_t frame[480*320],saved[360*192],original[480*320];
static uint32_t now_ms,press_started,release_after;
static unsigned samples,shutdowns,pixels,guard;
static uint16_t *memory(uint32_t a) {
    if(a==0xd0000000)return frame;
    assert(a==0xd0200000);return saved;
}
static void pixel(unsigned x,unsigned y,uint16_t color) {
    assert(x<480 && y<320);frame[y*480+x]=color;pixels++;
}
#define TX15_STANDALONE 1
#define TX15_POWER_UI_MEMORY(a) memory(a)
#define TX15_POWER_UI_PIXEL(x,y,c) pixel(x,y,c)
#include "src/target/tx/radiomaster/tx15/power_ui.c"
u32 CLOCK_getms(void){return now_ms;}
uint32_t tx15_power_status(void){
    return (uint32_t)(now_ms-press_started)<release_after?TX15_BUTTON_PRESSED:0;
}
int tx15_runtime_poll(unsigned now){
    (void)now;samples++;now_ms+=1;
    /* A service/draw path may itself reset the watchdog. No nested modal. */
    if(!guard){guard=1;tx15_power_ui_poll();guard=0;}
    return 1;
}
void PWR_Shutdown(void){
    assert(power_button.shutdown);assert(samples>100);
    shutdowns++;
}
static void reset(uint32_t start) {
    power_button=(struct tx15_power_button){0};power_busy=0;
    now_ms=start;press_started=start;release_after=0;
    samples=shutdowns=pixels=guard=0;
    for(unsigned i=0;i<480*320;i++)frame[i]=(uint16_t)(i^0xa55a);
    memcpy(original,frame,sizeof(frame));
    tx15_power_ui_poll();now_ms+=20;tx15_power_ui_poll();
    assert(power_button.released && !pixels && !shutdowns);
}
int main(void){
    /* Startup key must first be released; never show a shutdown countdown. */
    reset(0);power_button=(struct tx15_power_button){0};release_after=10000;
    tx15_power_ui_poll();assert(!pixels && !shutdowns);
    reset(0);press_started=now_ms;release_after=600;
    tx15_power_ui_poll();
    assert(!shutdowns && !power_busy && samples>=600 && pixels);
    assert(!memcmp(frame,original,sizeof(frame))); /* works for GUI or Lua */
    /* Cancelled holds do not accumulate. A new full hold uses all two seconds. */
    press_started=now_ms;release_after=UINT32_MAX;uint32_t started=now_ms;
    tx15_power_ui_poll();
    assert(shutdowns==1 && (uint32_t)(now_ms-started)>=2000);
    /* Modals only draw inside the saved rectangle. */
    for(unsigned y=0;y<320;y++)for(unsigned x=0;x<480;x++)
        if(x<60 || x>=420 || y<64 || y>=256)
            assert(frame[y*480+x]==original[y*480+x]);
    reset(0xfffffff0);press_started=now_ms;release_after=1000;
    tx15_power_ui_poll();assert(!shutdowns && !memcmp(frame,original,sizeof(frame)));
    reset(0xfffffff0);press_started=now_ms;release_after=UINT32_MAX;
    tx15_power_ui_poll();assert(shutdowns==1);
    return 0;
}
'''
class PowerUITests(unittest.TestCase):
    def test_shutdown_cancel_restore_and_live_service(self):
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'test.c';exe=Path(tmp)/'test.exe';src.write_text(HARNESS)
            include=['-I',str(ROOT),'-I',str(ROOT.parent/'tools/msys64/ucrt64/include')]
            for name in ('src','src/target/tx/radiomaster/tx15','src/target/drivers/filesystems','src/gui/320x240x16','src/pages/320x240x16'):
                include+=['-I',str(ROOT/name)]
            result=subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror',*include,
                str(src),str(ROOT/'hardware/tx15/boot/power_button.c'),'-o',str(exe)],
                capture_output=True,text=True,encoding='utf8',errors='replace',env=env)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            result=subprocess.run([str(exe)],capture_output=True,text=True,encoding='utf8',errors='replace',env=env,timeout=15)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
