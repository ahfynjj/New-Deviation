"""Native monitor state and physical trim-to-mixer regressions (no emulator)."""
import re
import tempfile
import struct
import zlib
import subprocess
from pathlib import Path
import unittest
import test_switch_upgrade as switches
ROOT=switches.ROOT

class DashboardTests(unittest.TestCase):
    run_c=switches.SwitchUpgradeTests.run_c

    def test_native_drawing_bounds_and_static_preview_use_real_font_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'draw.txt'
            program=r'''
#define USE_OWN_STDIO 0
#include <assert.h>
#include <stdio.h>
#include "common.h"
#include "config/display.h"
#include "input_dashboard.h"
struct display_settings Display;static unsigned font=1,color;
u8 LCD_SetFont(unsigned i){unsigned old=font;font=i;return old;}
void LCD_SetFontColor(u16 c){color=c;}
void LCD_PrintStringXY(unsigned x,unsigned y,const char *s){assert(x<480 && y<320);printf("T %u %u %u %u %s\n",x,y,font,color,s);}
void LCD_FillRect(u16 x,u16 y,u16 w,u16 h,u16 c){assert(w && h && x+w<=480 && y+h<=320);printf("F %u %u %u %u %u\n",x,y,w,h,c);}
void LCD_DrawRect(u16 x,u16 y,u16 w,u16 h,u16 c){assert(w && h && x+w<=480 && y+h<=320);printf("R %u %u %u %u %u\n",x,y,w,h,c);}
void LCD_DrawFastHLine(u16 x,u16 y,u16 w,u16 c){LCD_FillRect(x,y,w,1,c);}
void LCD_DrawFastVLine(int16_t x,int16_t y,int16_t h,u16 c){assert(x>=0 && y>=0 && h>0);LCD_FillRect(x,y,1,h,c);}
int main(void){
 assert(freopen(OUTPUT,"w",stdout));DEFAULT_FONT.font=1;TINY_FONT.font=2;
 struct tx15_dashboard_state s={.percent={100,-100,100,-100,-100,100},.analog_valid=1,
  .position={0,1,2,0,1,2},.trim={-1000,0,1900,-1},.trim_bound=15,.trim_pressed=0x81,.buttons=4,.selected=4};
 for(unsigned i=0;i<TX15_DASHBOARD_TILES;i++)tx15_dashboard_draw(i,&s);
 puts("FRAME");s.analog_valid=0;s.trim_bound=0;s.selected=-1;
 for(unsigned i=0;i<6;i++)s.position[i]=-1;
 for(unsigned i=0;i<TX15_DASHBOARD_TILES;i++)tx15_dashboard_draw(i,&s);
 return 0;
}'''.replace('OUTPUT','"'+output.as_posix()+'"')
            self.run_c(program,['src/target/tx/radiomaster/tx15/input_dashboard.c'])
            frames=output.read_text().split('FRAME\n')
            font=Path(tmp)/'15normal.fon'
            subprocess.run([str(ROOT.parent/'tools/msys64/usr/bin/perl.exe'),str(ROOT/'utils/font/bdf_to_font.pl'),
                '-maxsize','15','-mode','bin',str(ROOT/'src/fonts/15normal.bdf'),'-out',str(font),'-minspace','8','-ascii'],
                check=True,stdout=subprocess.DEVNULL)
            fonts={1:font.read_bytes(),2:(ROOT/'src/fs/base_fonts/media/5x7.fon').read_bytes()}
        folder=ROOT/'local/tx15-hardware/input-dashboard-20261012/app'
        folder.mkdir(parents=True,exist_ok=True)
        for n,frame in enumerate(frames):
            if not frame.strip():continue
            pixels=bytearray(bytes((16,24,32))*480*320)
            def rgb(c):return bytes((((c>>11)&31)*255//31,((c>>5)&63)*255//63,(c&31)*255//31))
            def pixel(x,y,c):
                self.assertTrue(0<=x<480 and 0<=y<320,(x,y))
                offset=(y*480+x)*3;pixels[offset:offset+3]=rgb(c)
            for line in frame.splitlines():
                kind,x,y,*rest=line.split();x=int(x);y=int(y)
                if kind=='T':
                    font,color,*words=rest;data=fonts[int(font)];height=data[0];rowbytes=(height+7)//8
                    ranges=[];pos=1
                    while True:
                        first,last=struct.unpack_from('<HH',data,pos);pos+=4
                        if first==last==0:break
                        ranges.append((first,last))
                    for ch in ' '.join(words):
                        index=0
                        for first,last in ranges:
                            if first<=ord(ch)<=last:index+=ord(ch)-first;break
                            index+=last-first+1
                        begin=int.from_bytes(data[pos+index*3:pos+index*3+3],'little')
                        end=int.from_bytes(data[pos+(index+1)*3:pos+(index+1)*3+3],'little')
                        width=(end-begin)//rowbytes
                        for col in range(width):
                            bits=int.from_bytes(data[begin+col*rowbytes:begin+(col+1)*rowbytes],'little')
                            for row in range(height):
                                if bits&(1<<row):pixel(x+col,y+row,int(color))
                        x+=width+1
                else:
                    w,h,color=map(int,rest)
                    for dy in range(h):
                        for dx in range(w):
                            if kind=='F' or dx in (0,w-1) or dy in (0,h-1):pixel(x+dx,y+dy,color)
            scan=b''.join(b'\0'+pixels[y*480*3:(y+1)*480*3] for y in range(320))
            def chunk(tag,data):return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data))
            png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',480,320,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b'')
            (folder/('preview-valid.png' if n==0 else 'preview-invalid.png')).write_bytes(png)

    def test_dashboard_reads_physical_axes_pressed_keys_and_custom_trim_values(self):
        self.run_c(r'''
#include <assert.h>
#include <string.h>
#include "common.h"
#include "config/model.h"
#include "input_dashboard.h"
#include "hardware/tx15/board/controls.h"
struct Model Model;struct tx15_controls tx15_controls;
volatile uint32_t tx15_analog_status;volatile uint16_t tx15_controls_raw[2];
static unsigned keys;
unsigned tx15_inputs_state(void){return keys;}
s32 CHAN_ReadInput(int ch){return (ch-3)*6000;}
s32 MIXER_GetTrimValue(int i){return i==6?-120:0;}
int main(void){
 struct tx15_dashboard_state s;memset(&Model,0,sizeof(Model));
 tx15_analog_status=4;tx15_controls.valid=(1u<<1)|(1u<<6);
 tx15_controls.position[1]=2;tx15_controls.position[6]=4;tx15_controls.buttons=1u<<2;
 tx15_controls_raw[0]=0xffff;tx15_controls_raw[1]=0xf57f;keys=1u<<(4+5);
 Model.trims[6].src=INP_RUDDER;Model.trims[6].pos=BUT_TRIM_LH_POS;Model.trims[6].neg=BUT_TRIM_LH_NEG;
 tx15_dashboard_collect(&s);
 assert(s.analog_valid && s.percent[0]==-100 && s.percent[1]==-60 && s.percent[5]==100);
 assert(s.position[0]==-1 && s.position[1]==2 && s.selected==4 && s.buttons==(1u<<2));
 assert(s.trim_bound==(1u<<2) && s.trim[2]==-12 && s.trim_pressed==(1u<<5));
 assert(s.raw[0]==0xffff && s.raw[1]==0xf57f);
 tx15_analog_status=0;tx15_controls.valid=0;tx15_dashboard_collect(&s);
 assert(!s.analog_valid && s.selected==-1 && s.position[1]==-1);
 return 0;
}''',['src/target/tx/radiomaster/tx15/input_dashboard.c'])

    def test_dashboard_enter_does_not_adjust_a_custom_enter_trim(self):
        self.run_c(r'''
#include <assert.h>
#include "common.h"
#include "gui/gui.h"
#include "config/display.h"
#include "config/model.h"
#include "config/tx.h"
#include "input_dashboard.h"
#include "hardware/tx15/board/controls.h"
struct Model Model;struct Transmitter Transmitter;struct display_settings Display;
struct tx15_controls tx15_controls;volatile uint32_t tx15_analog_status;volatile uint16_t tx15_controls_raw[2];
static u32 now,pressed;static unsigned hidden_calls;
u32 CLOCK_getms(void){return now;}u32 ScanButtons(void){return pressed;}
unsigned tx15_inputs_state(void){return 0;}s32 CHAN_ReadInput(int ch){(void)ch;return 0;}
void AUTODIMMER_Check(void){}
void SOUND_SetFrequency(unsigned a,unsigned b){(void)a;(void)b;}
void SOUND_StartWithoutVibrating(unsigned a,u16(*b)(void)){(void)a;(void)b;}
void GUI_SetHidden(guiObject_t *o,u8 h){(void)o;(void)h;hidden_calls++;}
void _GUI_Redraw(guiObject_t *o){(void)o;}
guiObject_t *GUI_CreateRectCB(guiRect_t *r,u16 x,u16 y,u16 w,u16 h,const struct LabelDesc *d,void(*cb)(guiObject_t*,const void*),const void *data){(void)x;(void)y;(void)w;(void)h;(void)d;(void)cb;(void)data;return (guiObject_t*)r;}
u8 LCD_SetFont(unsigned i){(void)i;return 0;}void LCD_SetFontColor(u16 c){(void)c;}
void LCD_PrintStringXY(unsigned x,unsigned y,const char*s){(void)x;(void)y;(void)s;}
void LCD_FillRect(u16 x,u16 y,u16 w,u16 h,u16 c){(void)x;(void)y;(void)w;(void)h;(void)c;}
void LCD_DrawRect(u16 x,u16 y,u16 w,u16 h,u16 c){(void)x;(void)y;(void)w;(void)h;(void)c;}
void LCD_DrawFastHLine(u16 x,u16 y,u16 w,u16 c){(void)x;(void)y;(void)w;(void)c;}
void LCD_DrawFastVLine(int16_t x,int16_t y,int16_t h,u16 c){(void)x;(void)y;(void)h;(void)c;}
int main(void){
 Model.trims[0].src=INP_S1;Model.trims[0].pos=BUT_ENTER;Model.trims[0].step=1;
 MIXER_RegisterTrimButtons();buttonAction_t action={0};tx15_input_dashboard_init(&action);
 now=100;pressed=CHAN_ButtonMask(BUT_ENTER);BUTTON_Handler();
 assert(*MIXER_GetTrim(0)==0 && hidden_calls==17);
 for(now=200;now<=800;now+=100)BUTTON_Handler();
 assert(*MIXER_GetTrim(0)==0 && hidden_calls==17);
 pressed=0;now=900;BUTTON_Handler();assert(*MIXER_GetTrim(0)==0 && hidden_calls==17);
 BUTTON_UnregisterCallback(&action);pressed=CHAN_ButtonMask(BUT_ENTER);now=1000;BUTTON_Handler();
 assert(*MIXER_GetTrim(0)==1); /* Scope ends when the page is left. */
 return 0;
}''',['src/target/tx/radiomaster/tx15/input_dashboard.c','src/buttons.c','src/mixer.c','src/inputs.c'])

    def test_product_template_binds_all_four_physical_trim_pairs(self):
        text=(ROOT/'hardware/tx15/app/model-crsf.ini').read_text()
        for i,axis in enumerate(('LEFT_V','RIGHT_V','LEFT_H','RIGHT_H'),1):
            section=re.search(r'\[trim%d\]\s*([^\[]+)'%i,text)
            self.assertIsNotNone(section, 'Product model has no trim%d binding'%i)
            self.assertIn('src='+axis,section[1])
            self.assertIn('pos=TRIM'+axis.replace('LEFT_','L').replace('RIGHT_','R')+'+',section[1])

    def test_empty_legacy_bindings_repaired_without_overwriting_custom_trims(self):
        self.run_c(r'''
#include <assert.h>
#include <string.h>
#include "common.h"
#include "config/model.h"
#include "trim_defaults.h"
int main(void) {
 struct Model m={0},saved;
 for(unsigned i=0;i<NUM_TRIMS;i++)m.trims[i].step=1;
 saved=m;assert(tx15_trim_defaults(&m));
 const unsigned src[]={2,3,4,1},pos[]={2,4,6,8},neg[]={1,3,5,7};
 for(unsigned i=0;i<4;i++)assert(m.trims[i].src==src[i] && m.trims[i].pos==pos[i] && m.trims[i].neg==neg[i]);
 assert(!tx15_trim_defaults(&m));
 assert(!memcmp(m.mixers,saved.mixers,sizeof(m.mixers)) && !memcmp(m.limits,saved.limits,sizeof(m.limits)));
 m=saved;m.trims[7].src=INP_S1;m.trims[7].pos=BUT_ENTER;m.trims[7].value[0]=17;saved=m;
 assert(!tx15_trim_defaults(&m) && !memcmp(&m,&saved,sizeof(m)));
 memset(&m,0,sizeof(m));m.trims[0].value[4]=19;saved=m;
 assert(!tx15_trim_defaults(&m) && !memcmp(&m,&saved,sizeof(m)));
 return 0;
}''',[])

    def test_physical_trim_presses_change_real_mixer_output_in_all_stick_modes(self):
        self.run_c(r'''
#include <assert.h>
#include <string.h>
#include "common.h"
#include "buttons.h"
#include "config/model.h"
#include "config/tx.h"
#include "trim_defaults.h"
struct Model Model;struct Transmitter Transmitter;
static u32 now,pressed;
u32 CLOCK_getms(void){return now;}
u32 ScanButtons(void){return pressed;}
void AUTODIMMER_Check(void){}
void SOUND_SetFrequency(unsigned a,unsigned b){(void)a;(void)b;}
void SOUND_StartWithoutVibrating(unsigned a,u16(*b)(void)){(void)a;(void)b;}
int main(void){
 for(unsigned mode=1;mode<=4;mode++){
  Transmitter.mode=mode;memset(&Model,0,sizeof(Model));
  assert(tx15_trim_defaults(&Model));MIXER_RegisterTrimButtons();
  for(unsigned i=0;i<4;i++){
   now+=100;pressed=CHAN_ButtonMask(Model.trims[i].pos);BUTTON_Handler();
   assert(*MIXER_GetTrim(i)==1);
   volatile s32 values[NUM_SOURCES+1]={0};s32 original=0;
   struct Mixer mx={0};mx.src=MIXER_MapChannel(Model.trims[i].src);mx.scalar=100;
   MIXER_SET_APPLY_TRIM(&mx,1);MIXER_ApplyMixer(&mx,values,&original);
   assert(values[NUM_INPUTS+1]==10); /* 0.1%, using the actual mixer. */
   MIXER_SET_APPLY_TRIM(&mx,0);MIXER_ApplyMixer(&mx,values,&original);
   assert(values[NUM_INPUTS+1]==0);
   now+=100;pressed=0;BUTTON_Handler();
   now+=100;pressed=CHAN_ButtonMask(Model.trims[i].neg);BUTTON_Handler();
   assert(*MIXER_GetTrim(i)==0);
   now+=100;pressed=0;BUTTON_Handler();
  }
  now+=100;pressed=CHAN_ButtonMask(Model.trims[0].pos);BUTTON_Handler();
  assert(*MIXER_GetTrim(0)==1);
  now+=510;BUTTON_Handler();assert(*MIXER_GetTrim(0)==10);
  now+=100;pressed=0;BUTTON_Handler();assert(*MIXER_GetTrim(0)==10);
 }
 return 0;
}''',['src/mixer.c','src/buttons.c','src/curves.c','src/inputs.c'])

