"""Actual TX15 input decoder, debounce, and model trim regressions."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class ControlsTests(unittest.TestCase):
    def test_expander_mapping_debounce_latch_and_invalid_contacts(self):
        source = ROOT/'hardware/tx15/board/control_decode.c'
        self.assertTrue(source.exists(), 'Switch/trim expander decoder missing')
        program = r'''
#include <assert.h>
#include "hardware/tx15/board/controls.h"
int main(void) {
 struct tx15_controls c;
 tx15_controls_reset(&c);
 assert(tx15_controls_switch(&c,0,0)==-1);
 tx15_controls_decode(&c,0xffff,0xffff,0);
 tx15_controls_decode(&c,0xffff,0xffff,20);
 for(unsigned i=0;i<4;i++) {
  assert(tx15_controls_switch(&c,i,1)==1);
  assert(tx15_controls_switch(&c,i,0)==0);
 }
 assert(tx15_controls_switch(&c,4,0)==1);
 assert(tx15_controls_switch(&c,5,0)==1);
 const unsigned hi[]={13,11,9,7},lo[]={12,10,8,6};
 for(unsigned i=0;i<4;i++) {
  tx15_controls_decode(&c,0xffff,0xffff^(1u<<lo[i]),30+i*100);
  assert(tx15_controls_switch(&c,i,1)==1); /* Debounce. */
  tx15_controls_decode(&c,0xffff,0xffff^(1u<<lo[i]),50+i*100);
  assert(tx15_controls_switch(&c,i,0)==1);
  tx15_controls_decode(&c,0xffff,0xffff^(1u<<hi[i]),60+i*100);
  tx15_controls_decode(&c,0xffff,0xffff^(1u<<hi[i]),80+i*100);
  assert(tx15_controls_switch(&c,i,2)==1);
  tx15_controls_decode(&c,0xffff,0xffff^((1u<<hi[i])|(1u<<lo[i])),90+i*100);
  assert(tx15_controls_switch(&c,i,0)==-1); /* Invalid pair never active. */
  tx15_controls_decode(&c,0xffff,0xffff,100+i*100);
  tx15_controls_decode(&c,0xffff,0xffff,120+i*100);
 }
 const unsigned trim_pins[]={12,13,10,11,15,14,9,8};
 for(unsigned i=0;i<8;i++) {
  tx15_controls_decode(&c,0xffff^(1u<<trim_pins[i]),0xffff,500+i);
  assert(c.trims==(1u<<i));
 }
 tx15_controls_decode(&c,0xffff,0xffff^(1u<<14),600);
 tx15_controls_decode(&c,0xffff,0xffff^(1u<<14),620);
 assert(tx15_controls_switch(&c,4,1)==1);
 tx15_controls_decode(&c,0xffff,0xffff^(1u<<5),630);
 tx15_controls_decode(&c,0xffff,0xffff^(1u<<5),650);
 assert(tx15_controls_switch(&c,5,1)==1);
 /* Six front buttons live on 0x74 and latch a selected position. */
 for(unsigned i=0;i<6;i++) {
  tx15_controls_decode(&c,0xffff^(1u<<i),0xffff,700+i*50);
  tx15_controls_decode(&c,0xffff^(1u<<i),0xffff,720+i*50);
  assert(tx15_controls_switch(&c,6,i)==1);
  tx15_controls_decode(&c,0xffff,0xffff,725+i*50);
  tx15_controls_decode(&c,0xffff,0xffff,745+i*50);
  assert(tx15_controls_switch(&c,6,i)==1);
 }
 tx15_controls_decode(&c,0xfffc,0xffff,1100);
 tx15_controls_decode(&c,0xfffc,0xffff,1120);
 assert(tx15_controls_switch(&c,6,5)==1); /* Ambiguous press ignored. */
 tx15_controls_invalidate(&c);
 assert(c.trims==0);
 for(unsigned i=0;i<7;i++) assert(tx15_controls_switch(&c,i,0)==-1);
 /* Old contact candidates must not become valid immediately after outage. */
 tx15_controls_decode(&c,0xffff,0xffff,1200);
 assert(tx15_controls_switch(&c,0,1)==-1);
 tx15_controls_decode(&c,0xffff,0xffff,1220);
 assert(tx15_controls_switch(&c,0,1)==1);
 return 0;
}
'''
        self.compile_run(program, [source])

    def test_eight_trim_buttons_are_debounced_and_released(self):
        self.compile_run(r'''
#include <assert.h>
#include "hardware/tx15/board/inputs.h"
int main(void) {
 struct tx15_input_filter f;
 tx15_input_filter_init(&f,0,3);
 for(unsigned n=4;n<12;n++) {
  for(unsigned i=0;i<19;i++) assert(!tx15_input_filter_step(&f,1u<<n,3).pressed);
  assert(tx15_input_filter_step(&f,1u<<n,3).pressed==(1u<<n));
  assert(f.stable==(1u<<n));
  for(unsigned i=0;i<20;i++) tx15_input_filter_step(&f,0,3);
  assert(!f.stable);
 }
 return 0;
}
''', [ROOT/'hardware/tx15/board/input_filter.c'])

    def test_i2c_reads_correct_ports_and_faults_do_not_activate_inputs(self):
        self.assertTrue((ROOT/'hardware/tx15/board/controls.c').exists(), 'I2C expander reader missing')
        self.compile_run(r'''
#include <assert.h>
#include <stdint.h>
static unsigned tick,reads,phase,byte_no,reg_written,address,fail_nack,stuck;
static uint32_t cr2,other[128];
static uint16_t ports[2]={0xfffb,0xefff};
static uint32_t rd(uint32_t a) {
 assert(++reads<50000);
 if(a==0x2400e02c) return tick+reads/100;
 if(a==0x58024400) return 5; /* HSI ready, undivided. */
 if(a==0x58001c04) return cr2;
 if(a==0x58001c18) {
  if(stuck) return 0x8000;
  if(fail_nack && phase) return 16;
  if(phase==1) return reg_written?64:2;
  if(phase==2) return byte_no<2?4:32;
  return 0;
 }
 if(a==0x58001c24) {
  assert(phase==2 && byte_no<2);
  unsigned result=(ports[address-0x74]>>(byte_no*8))&255;byte_no++;return result;
 }
 return other[(a>>2)&127];
}
static void wr(uint32_t a,uint32_t v) {
 /* No flash, RF, touch, expander output, DMA or interrupt writes. */
 assert((a>=0x58001c00 && a<=0x58001c28) ||
        (a>=0x58024400 && a<=0x580244f4) ||
        (a>=0x58020c00 && a<=0x58020c24) ||
        (a>=0x58021800 && a<=0x58021824));
 if(a==0x58001c04) {
  cr2=v;
  if(v&(1u<<13)) {
   address=(v>>1)&127; assert(address==0x74 || address==0x75);
   if(v&(1u<<10)) {assert(((v>>16)&255)==2 && (v&(1u<<25)));phase=2;byte_no=0;}
   else {assert(((v>>16)&255)==1 && !(v&(1u<<25)));phase=1;reg_written=0;}
  }
 }
 if(a==0x58001c28) {assert(phase==1 && v==0);reg_written=1;}
 if(a==0x58001c1c) phase=0;
 other[(a>>2)&127]=v;
}
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#include "hardware/tx15/board/controls.c"
int main(void) {
 assert(tx15_controls_init()==0);
 assert(tx15_controls_raw[0]==ports[0] && tx15_controls_raw[1]==ports[1]);
 assert(tx15_controls_status==1);
 tick=100;reads=0; tx15_controls_poll(100);
 assert(tx15_controls_switch(&tx15_controls,0,0)==1);
 assert(tx15_controls_switch(&tx15_controls,6,2)==1);
 fail_nack=1;tick=110;reads=0;tx15_controls_poll(110);
 assert(tx15_controls_status==2 && tx15_controls_errors==1 && !tx15_controls.trims);
 assert(tx15_controls_switch(&tx15_controls,0,0)==-1);
 fail_nack=0;stuck=1;tick=1200;reads=0;tx15_controls_poll(1200);
 assert(tx15_controls_status==2 && tx15_controls_errors==2);
 assert(reads<20000);
 return 0;
}
''', [ROOT/'hardware/tx15/board/control_decode.c'])

    def test_default_native_model_has_all_four_physical_trims(self):
        import configparser
        cfg = configparser.ConfigParser(strict=False)
        cfg.read_string('[model]\n'+(ROOT/'hardware/tx15/app/model.ini').read_text(encoding='utf8'))
        for i,name in enumerate(('LV','RV','LH','RH'),1):
            self.assertIn('trim'+str(i), cfg)
            self.assertEqual(cfg['trim'+str(i)]['neg'], 'TRIM'+name+'-')
            self.assertEqual(cfg['trim'+str(i)]['pos'], 'TRIM'+name+'+')

    def compile_run(self, program, sources):
        gcc = Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env = dict(os.environ, PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as folder:
            src = Path(folder)/'test.c'
            src.write_text(program, encoding='ascii')
            exe = Path(folder)/'test.exe'
            result = subprocess.run([str(gcc),'-std=c11','-Wall','-Wextra','-Werror',
                '-isystem',str(gcc.parent.parent/'include'),'-I',str(ROOT),str(src),
                *map(str,sources),'-o',str(exe)],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            result = subprocess.run([str(exe)],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
