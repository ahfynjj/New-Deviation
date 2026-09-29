import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import display_session as d

class DisplayTests(unittest.TestCase):
    def test_landscape_mapping_covers_framebuffer_once(self):
        root=Path(__file__).resolve().parents[3]
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'mapping.c'; binary=Path(tmp)/'mapping.exe'
            source.write_text('''
#include <assert.h>
#include "hardware/tx15/board/display.h"
static unsigned char seen[TX15_LCD_BYTES/2];
int main(void) {
 for(unsigned x=0;x<480;x++) for(unsigned y=0;y<320;y++) {
  unsigned i=tx15_display_offset(x,y); assert(i<153600); assert(!seen[i]); seen[i]=1;
 }
 for(unsigned i=0;i<153600;i++) assert(seen[i]);
 assert(tx15_display_offset(0,0)==0);
 assert(tx15_display_offset(1,0)==1);
 assert(tx15_display_offset(0,1)==480);
 assert(tx15_display_offset(479,319)==153599);
}
''')
            env=dict(os.environ, PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
            subprocess.run([str(gcc),'-I',str(gcc.parent.parent/'include'),'-I',str(root),str(source),'-o',str(binary)],check=True,env=env,capture_output=True)
            subprocess.run([str(binary)],check=True,env=env)

    def mock(self):
        regs={a:0 for a in d.CONTROL_ADDRS}
        regs[d.AHB4]=0x81; regs[d.DIV3]=0x01010200
        def read(a): return regs.get(a,0)
        def write(a,v):
            regs[a]=v
            if a==d.CR: regs[a]=v & ~(1<<29) if not v&(1<<28) else v|(1<<29)
            if a==d.RST3 and v&8: regs[0x50001018]=0x2220
            for p in d.PORTS:
                b=0x58020000+p*0x400
                if a==b+24: regs[b+20]=(regs[b+20]|(v&0xffff))&~(v>>16)
        return regs,read,write

    def test_restore_disables_scan_before_pll_and_restores_gpio(self):
        regs,read,write=self.mock(); saved=d.capture(read,write); trace=[]
        regs[d.CR]=0x33030005; regs[d.APB3]=8; regs[0x50001018]=0x10012221
        regs[d.SEL]=12<<20; regs[d.CFG]=0x01000800; regs[d.DIV3]=0x1701023f
        def traced(a,v): trace.append(a); write(a,v)
        self.assertTrue(d.restore(read,traced,saved))
        self.assertLess(trace.index(d.RST3),trace.index(d.CR))
        self.assertEqual(regs[d.AHB4],saved[d.AHB4])
        self.assertEqual(regs[d.CR]&0x30000000,0)

    def test_pll_stop_failure_blocks_resume(self):
        regs,read,write=self.mock(); saved=d.capture(read,write); regs[d.CR]=0x30000000
        def stuck(a,v):
            if a!=d.CR: write(a,v)
        with self.assertRaisesRegex(RuntimeError,'PLL3 stop timeout'): d.restore(read,stuck,saved,budget=2)

    def test_capture_cleanup_failure_is_not_safe_to_resume(self):
        regs,read,write=self.mock()
        def stuck(a,v):
            if not (a==d.AHB4 and v==0x81): write(a,v)
        with self.assertRaises(d.DisplayCaptureRecoveryError): d.capture(read,stuck)
