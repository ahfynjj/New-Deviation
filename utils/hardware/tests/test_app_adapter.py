import os, subprocess, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class AdapterTests(unittest.TestCase):
 def test_pixel_order_and_real_deviation_font_via_romfs(self):
  gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
  with tempfile.TemporaryDirectory() as tmp:
   src=Path(tmp)/'adapter.c'; exe=Path(tmp)/'adapter.exe'
   font=(ROOT/'src/fs/base_fonts/media/14bold.fon').read_bytes()
   scan=(ROOT/'src/target/tx/radiomaster/tx15/platform.c').read_text().split('u32 ScanButtons(void) {',1)[1].split('void SysTick_Handler',1)[0]
   source=r"""
#include <assert.h>
#include "common.h"
#include "screen/font.h"
#include "romfs.h"
#include "buttons.h"
#include "config/tx.h"
struct Transmitter Transmitter;
volatile uint16_t tx15_analog_raw[6];
volatile uint32_t tx15_analog_status,tx15_analog_frames;
#include "hardware/tx15/board/inputs.h"
static unsigned up_releases, down_releases;
void AUTODIMMER_Check(void) {}
static unsigned count_action(u32 button,unsigned flags,void *data) {
 (void)data;
 if(flags & BUTTON_RELEASE) {
  if(button==CHAN_ButtonMask(BUT_UP)) up_releases++;
  if(button==CHAN_ButtonMask(BUT_DOWN)) down_releases++;
 }
 return 1;
}
static u32 test_ms; static int rotation;
u32 CLOCK_getms(void) { return test_ms; }
unsigned tx15_inputs_state(void) { return 0; }
struct tx15_input_event tx15_inputs_take(void) { struct tx15_input_event e={0,rotation}; rotation=0; return e; }
u32 ScanButtons(void) { SCANBODY

static const uint8_t data[]={FONTBYTES};
const struct tx15_resource tx15_resources[]={{"media/14bold.fon",data,sizeof(data)}};
const size_t tx15_resource_count=1;
static unsigned px[8],py[8],n;
void tx15_display_pixel(unsigned x,unsigned y,uint16_t c) { (void)c; assert(n<8);px[n]=x;py[n++]=y; }
int main(void) {
 tx15_analog_status=4;
 tx15_analog_raw[0]=100;tx15_analog_raw[1]=200;tx15_analog_raw[2]=300;
 tx15_analog_raw[3]=400;tx15_analog_raw[4]=500;tx15_analog_raw[5]=600;
 assert(CHAN_ReadRawInput(INP_AILERON)==3695);
 assert(CHAN_ReadRawInput(INP_ELEVATOR)==3895); /* physical LV; Mode 2 swaps in mixer */
 assert(CHAN_ReadRawInput(INP_THROTTLE)==300);  /* physical RV */
 assert(CHAN_ReadRawInput(INP_RUDDER)==100);
 assert(CHAN_ReadRawInput(INP_S1)==3595 && CHAN_ReadRawInput(INP_S2)==3495);
 Transmitter.calibration[3]=(struct StickCalibration){3000,1000,2000};
 tx15_analog_raw[0]=1000;assert(CHAN_ReadInput(INP_RUDDER)==-10000);
 tx15_analog_raw[0]=2000;assert(CHAN_ReadInput(INP_RUDDER)==0);
 tx15_analog_raw[0]=4095;assert(CHAN_ReadInput(INP_RUDDER)==10000);
 tx15_analog_status=6;assert(CHAN_ReadInput(INP_THROTTLE)==-10000);
 assert(CHAN_ReadInput(INP_AILERON)==0);
 rotation=1; assert(ScanButtons()==CHAN_ButtonMask(BUT_DOWN));
 test_ms=100; assert(ScanButtons()==0);
 test_ms=200; rotation=-1; assert(ScanButtons()==CHAN_ButtonMask(BUT_UP));
 test_ms=300; assert(ScanButtons()==0);
 buttonAction_t action={0};
 BUTTON_RegisterCallback(&action,CHAN_ButtonMask(BUT_UP)|CHAN_ButtonMask(BUT_DOWN),
   BUTTON_PRESS|BUTTON_RELEASE,count_action,0);
 /* Feed ten detent events each way through the real Deviation debounce and
  * callback dispatcher. GUI navigation consumes the release, not the press. */
 for(test_ms=500;test_ms<6500;test_ms+=5) {
  if(test_ms>=1000 && test_ms<3500 && (test_ms-1000)%250==0) rotation=-1;
  if(test_ms>=3500 && test_ms<6000 && (test_ms-3500)%250==0) rotation=1;
  BUTTON_Handler();
 }
 assert(up_releases==10 && down_releases==10);
 LCD_DrawStart(4,5,5,6,DRAW_NWSE);
 for(int i=0;i<5;i++) LCD_DrawPixel(1);
 assert(n==4 && px[0]==4 && py[0]==5 && px[3]==5 && py[3]==6);
 n=0; LCD_DrawStart(4,5,5,6,DRAW_SWNE);
 for(int i=0;i<4;i++) LCD_DrawPixel(1);
 assert(py[0]==6 && py[3]==5);
 n=0; LCD_DrawStart(5,5,4,6,DRAW_NWSE);LCD_DrawPixel(1);assert(!n);
 assert(!fopen("media/14bold.fon","wb"));
 assert(!fopen("missing","rb"));
 FILE *f=fopen("media/14bold.fon","rb"); assert(f);
 assert(fseek(f,-1,SEEK_SET)==-1 && ftell(f)==0);
 assert(fseek(f,-1,SEEK_END)==0);
 uint8_t b[4]; assert(fread(b,2,1,f)==0); assert(ftell(f)==sizeof(data));
 assert(fwrite(b,1,1,f)==0);assert(fclose(f)==0);assert(fclose(f)==-1);
 assert(open_font("14bold"));assert(get_height()==data[0]);
 uint8_t glyph[CHAR_BUF_SIZE]={0},width=0;
 char_read(glyph,'A',&width);assert(width>0 && width<32);
 assert(get_width('A')==width);unsigned bits=0;
 for(unsigned i=0;i<sizeof(glyph);i++) bits|=glyph[i];assert(bits);
 close_font();return 0;
}
""".replace('SCANBODY',scan).replace('FONTBYTES',','.join(str(b) for b in font))
   src.write_text(source)
   includes=['-I',str(ROOT),'-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),'-I',str(gcc.parent.parent/'include')]
   for d in ('src','src/target/tx/radiomaster/tx15','src/target/drivers/filesystems','src/gui/320x240x16','src/pages/320x240x16'):
    includes+=['-I',str(ROOT/d)]
   env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
   cmd=[str(gcc),'-DUSE_OWN_PRINTF=0',*includes,str(src),str(ROOT/'src/target/tx/radiomaster/tx15/lcd.c'),str(ROOT/'src/target/tx/radiomaster/tx15/romfs.c'),str(ROOT/'src/screen/font.c'),str(ROOT/'src/buttons.c'),str(ROOT/'src/target/tx/radiomaster/tx15/analog.c'),'-o',str(exe)]
   r=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace",env=env)
   self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   subprocess.run([str(exe)],check=True,env=env)
