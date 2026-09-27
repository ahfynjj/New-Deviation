"""Native PLL sequencing at the MMIO boundary; no physical board simulation."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class PllTests(unittest.TestCase):
    def test_lock_switch_prescalers_and_failure_paths(self):
        self.assertTrue((ROOT / 'hardware/tx15/board/pll.c').exists())
        native = Path(tempfile.gettempdir()) / 'new-deviation-ucrt64/bin'
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'test.c'
            source.write_text(r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
static uint32_t r[14], power, supply, flash;
static unsigned reads, writes, lock_polls, switch_polls;
static int fail_lock, fail_switch, fail_divider, fail_config;
static uint32_t rd(uint32_t a) {
    assert(++reads < 300);
    if (a == 0x58024804) return power;
    if (a == 0x5802480c) return supply;
    if (a == 0x52002000) return flash;
    assert(a>=0x58024400 && a<=0x58024434 && !(a&3));
    if (a==0x58024400 && (r[0]&0x1000000) && !fail_lock && ++lock_polls>=3) r[0]|=0x2000000;
    if (a==0x58024410 && (r[4]&7)==3 && !fail_switch && ++switch_polls>=3) r[4]=(r[4]&~0x38)|0x18;
    return r[(a-0x58024400)/4];
}
static void wr(uint32_t a, uint32_t v) {
    ++writes;
    assert(a>=0x58024400 && a<=0x58024430 && !(a&3));
    if (a>=0x58024428) assert(!(r[0]&0x3000000));
    if(a==0x58024410) {
        assert((r[0]&0x3000000)==0x3000000);
        assert((r[6]&0xf7f)==0x48 && (r[7]&0x770)==0x440 && (r[8]&0x70)==0x40);
    }
    if (fail_divider && a==0x58024418) return;
    if (fail_config && a==0x58024428) return;
    r[(a-0x58024400)/4]=v;
}
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#include "hardware/tx15/board/pll.c"
static void reset(void) {
    memset(r,0,sizeof(r)); r[0]=0x34025; r[4]=0x8012;
    r[10]=0xabc00000; r[11]=0x01ff0fffu; r[12]=0x01010280;
    power=0x6000; supply=2; flash=7;
    reads=writes=lock_polls=switch_polls=0; fail_lock=fail_switch=fail_divider=fail_config=0;
}
int main(void) {
    reset(); assert(tx15_clock_pll128_init(8)==TX15_CLOCK_OK);
    assert(r[0]==0x3034025 && r[4]==0x801b);
    assert(r[10]==0xabc000c2 && r[11]==0x01f90ff8 && r[12]==0x0101023f);
    reset(); fail_lock=1; assert(tx15_clock_pll128_init(8)==TX15_CLOCK_PLL_TIMEOUT); assert((r[4]&0x3f)==0x12);
    reset(); fail_switch=1; assert(tx15_clock_pll128_init(8)==TX15_CLOCK_SWITCH_TIMEOUT); assert((r[0]&5)==5);
    reset(); fail_divider=1; assert(tx15_clock_pll128_init(8)==TX15_CLOCK_BAD_STATE); assert((r[4]&7)==2);
    reset(); fail_config=1; assert(tx15_clock_pll128_init(8)==TX15_CLOCK_BAD_STATE); assert(!(r[0]&0x1000000));
    for(unsigned i=0;i<8;i++) {
        reset();
        if(i==0)power=0x4000; if(i==1)supply=3; if(i==2)flash=0;
        if(i==3)r[0]|=0x1000000; if(i==4)r[4]=0; if(i==5)r[7]=0x10;
        if(i==6)power=0x2000; if(i==7)r[0]&=~4u;
        assert(tx15_clock_pll128_init(8)==TX15_CLOCK_BAD_STATE); assert(!writes);
    }
}
''', encoding='ascii')
            env = os.environ.copy()
            env['PATH'] = str(native) + os.pathsep + env['PATH']
            exe = Path(tmp) / 'test.exe'
            p = subprocess.run([str(native/'gcc.exe'), '-std=c11', '-Wall', '-Wextra',
                '-Werror', '-Wno-misleading-indentation', '-isystem', str(native.parent/'include'),
                '-I.', str(source), '-o', str(exe)], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
            p = subprocess.run([str(exe)], env=env, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
