"""Screen renders every protocol state within the native landscape bounds."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[3]
HARNESS=r'''
#include <assert.h>
#include <string.h>
#include "screen.h"
static unsigned pixels,fills;
void tx15_display_pixel(unsigned x,unsigned y,unsigned short color) {
    (void)color;assert(x<480 && y<320);pixels++;
}
void tx15_display_fill(unsigned short c){(void)c;fills++;}
int main(void){
    struct tx15_update_reply s={0};
    for(unsigned i=0;i<=TX15_ERROR;i++) {
        s.state=i;s.error=i==TX15_ERROR;s.total=100;s.received=100;
        pixels=0;tx15_update_screen(&s,i%2,i%2);assert(pixels>5040);
    }
    s.total=0;s.received=0xffffffffu;tx15_update_screen(&s,0,0);
    assert(fills==10);
    for(unsigned stage=0;stage<3;stage++) {
        unsigned before=fills;pixels=0;tx15_boot_screen(stage,0,100);
        assert(fills==before+1 && pixels>5040);
        tx15_boot_screen(stage,50,100);assert(fills==before+1);
        tx15_boot_screen(stage,100,100);assert(fills==before+1);
        tx15_boot_screen(stage,0xffffffffu,0);
    }
    return 0;
}
'''
class ScreenTests(unittest.TestCase):
    def test_states_and_bounds(self):
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);c=folder/'test.c';c.write_text(HARNESS);exe=folder/'test.exe'
            r=subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror',
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),
                '-I',str(ROOT/'hardware/tx15/usb_update'),str(c),
                str(ROOT/'hardware/tx15/usb_update/screen.c'),'-o',str(exe)],env=env,
                capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stderr)
            r=subprocess.run([str(exe)],env=env,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
