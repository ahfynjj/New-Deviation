"""Run SDRAM driver with register/memory boundary injection, including alias faults."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[3]

class SdramTests(unittest.TestCase):
    def test_pin_scope_commands_and_memory_failures(self):
        self.assertTrue((ROOT/'hardware/tx15/board/sdram.c').exists())
        native = Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin'
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'test.c'
            src.write_text(r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
static uint32_t regs[128], addresses[128], mem[16384];
static unsigned used, writes, commands, delays;
static int alias, bad_clock, bad_config;
static uint32_t *reg(uint32_t a) {
    for(unsigned i=0;i<used;i++) if(addresses[i]==a) return &regs[i];
    assert(used<128); addresses[used]=a; regs[used]=0; return &regs[used++];
}
static uint32_t rd(uint32_t a) {
    if(a>=0xd0000000 && a<0xd0010000) return mem[(alias && a==0xd000fffc)?0:(a-0xd0000000)/4];
    if(a==0x58024410) return bad_clock?0:0x1b;
    if(a==0x58024418) return 0x48;
    if(a==0x58024428) return 0xc2;
    if(a==0x5802442c) return 0x10008;
    if(a==0x58024430) return 0x23f;
    if(a==0x58024400) return 0x3034025;
    return *reg(a);
}
static void wr(uint32_t a,uint32_t v) {
    ++writes;
    if(a>=0xd0000000 && a<0xd0010000) {
        assert(commands==4); mem[(alias && a==0xd000fffc)?0:(a-0xd0000000)/4]=v; return;
    }
    assert((a>=0x58020800 && a<=0x58021c24) || a==0x580244d4 || a==0x580244e0
           || a==0x52004000 || (a>=0x52004140 && a<=0x52004154));
    if(a==0x52004150) {
        const uint32_t expected[]={9,10,0xeb,0x4620c};
        assert(commands<4 && v==expected[commands]);
        if(commands) assert(delays>=commands);
        commands++;
    }
    if(bad_config && a==0x52004144) return;
    *reg(a)=v;
}
static void delay(uint32_t cycles) { assert(cycles>=12800); ++delays; }
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#define TX15_SDRAM_DELAY(n) delay(n)
#define TX15_SDRAM_BARRIER() ((void)0)
#include "hardware/tx15/board/sdram.c"
static void reset(void) {
    used=writes=commands=delays=0; alias=bad_clock=bad_config=0;
    for(unsigned port=2;port<=7;port++) for(unsigned offset=0;offset<=36;offset+=4)
        *reg(0x58020000+port*0x400+offset)=0xa5a5a5a5;
}
int main(void) {
    struct tx15_sdram_report r={0};
    reset(); assert(tx15_sdram_test(&r)==0);
    assert(r.state==3 && r.words==16384 && r.checks==32800 && !r.error);
    assert(commands==4 && rd(0x52004154)==460);
    /* PH12 power hold and every non-SDRAM pin must survive. */
    const uint32_t pins[]={0x1,0xc703,0xff83,0xf83f,0x8133,0xc0};
    for(unsigned p=0;p<6;p++) {
        uint32_t base=0x58020800+p*0x400;
        for(unsigned pin=0;pin<16;pin++) {
            unsigned m=(rd(base)>>(pin*2))&3;
            if(pins[p]&(1u<<pin)) assert(m==2 && ((rd(base+32+(pin/8)*4)>>((pin%8)*4))&15)==12);
            else assert(m==((0xa5a5a5a5u>>(pin*2))&3));
        }
    }
    reset(); memset(&r,0,sizeof(r)); alias=1;
    assert(tx15_sdram_test(&r)!=0 && r.error==3 && r.bad_address>=0xd0000000);
    reset(); memset(&r,0,sizeof(r)); bad_clock=1;
    assert(tx15_sdram_test(&r)!=0 && !writes);
    reset(); memset(&r,0,sizeof(r)); bad_config=1;
    assert(tx15_sdram_test(&r)!=0 && !commands);
}
''',encoding='ascii')
            env=os.environ.copy(); env['PATH']=str(native)+os.pathsep+env['PATH']
            exe=Path(tmp)/'test.exe'
            p=subprocess.run([str(native/'gcc.exe'),'-std=c11','-Wall','-Wextra','-Werror',
                '-isystem',str(native.parent/'include'),'-I.',str(src),'-o',str(exe)],
                cwd=ROOT,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            p=subprocess.run([str(exe)],env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
