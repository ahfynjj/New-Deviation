"""Real display init: measured delays, wraparound, bounded timer failure."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
HARNESS = r'''
#include <assert.h>
#include <stdint.h>
static uint32_t addresses[256],values[256],elapsed;
static unsigned used,advances;
static int running;
static uint32_t *slot(uint32_t a) {
    unsigned i;
    for(i=0;i<used;i++)if(addresses[i]==a)break;
    if(i==used){assert(used<256);addresses[used]=a;values[used++]=0;}
    if(a==0x58024400 && (values[i]&(1u<<28)))values[i]|=1u<<29;
    if(a==0xe0001004 && running && advances){
        values[i]+=6400;elapsed+=6400;advances--;
    }
    return values+i;
}
#define TX15_DISPLAY_REGISTER(a) (*slot(a))
#define TX15_DISPLAY_BARRIER() ((void)0)
#include "hardware/tx15/board/display.c"
static void reset(uint32_t start) {
    used=elapsed=0;running=0;advances=100000;
    *slot(0x58024400)=0x03030005;
    *slot(0x58024410)=0x1b;*slot(0x58024418)=0x48;
    *slot(0xe0001fb4)=3; /* cold M7 DWT locked */
    *slot(0xe0001004)=start;
    *slot(0x58022000)=0x12345678; /* preserve status LED pin modes */
    running=1;
}
int main(void) {
    reset(0xffff0000);
    assert(tx15_display_init()==0);
    assert(elapsed>=474u*128000u && elapsed<520u*128000u);
    assert(*slot(0xe0001fb0)==0xc5acce55); /* unlock before enabling */
    assert(*slot(0xe0001000)&1);
    assert((*slot(0x58022000)&0x00f30000)==(0x12345678&0x00f30000));
    reset(1234);running=0;
    assert(tx15_display_init()==3); /* bounded failure, no blind wait */
    assert(!*slot(0x58020018)); /* panel/backlight not touched */
    reset(1234);*slot(0xe0001000)=1u<<25;
    assert(tx15_display_init()==3); /* hardware has no cycle counter */
    reset(1234);advances=5;
    assert(tx15_display_init()==3); /* timer stopping during init is bounded */
    return 0;
}
'''


class DisplayStartupTests(unittest.TestCase):
    def test_actual_panel_sequence_uses_real_milliseconds(self):
        gcc = Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env = dict(os.environ, PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'test.c'; exe = Path(tmp)/'test.exe'
            source.write_text(HARNESS)
            built = subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror',
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),'-I',str(ROOT),
                str(source),'-o',str(exe)],env=env,capture_output=True,text=True,
                encoding='utf8',errors='replace')
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            result = subprocess.run([str(exe)],env=env,capture_output=True,text=True,
                encoding='utf8',errors='replace',timeout=15)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
