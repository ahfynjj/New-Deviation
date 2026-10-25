"""Actual native draw paths never expose erase/repaint before acknowledged swap."""
import unittest
import test_switch_upgrade as switches

HARDWARE = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#define TX15_FRAME_SWAP 1
#include "hardware/tx15/board/display.h"
static uint32_t frame_a[TX15_LCD_BYTES/4],frame_b[TX15_LCD_BYTES/4];
static uint32_t hw_ltdc[80],hw_dma[24],hw_clock=0x1001,cycles_fake;
static unsigned pending_swap,pending_dma,hold_swap,fail_dma,hang_dma;
static uint32_t scan_address=TX15_LCD_FB;
static unsigned serviced,clones,swaps;
static uint32_t *frame_memory(uint32_t a){
 assert(a==TX15_LCD_FB || a==0xd0100000);return a==TX15_LCD_FB?frame_a:frame_b;
}
static uint32_t frame_cycles(void){cycles_fake+=12800;return cycles_fake;}
static uint32_t frame_read(uint32_t a){
 if(a==0x580244d4)return hw_clock;
 if(a==0x5802447c)return 0;
 if(a>=0x50001000 && a<0x50001140){
  if(a==0x50001024 && pending_swap && !hold_swap && !--pending_swap){
   scan_address=hw_ltdc[0xac/4];hw_ltdc[0x24/4]=0;swaps++;
  }
  return hw_ltdc[(a-0x50001000)/4];
 }
 assert(a>=0x52001000 && a<0x52001060);
 if(a==0x52001004 && pending_dma && !hang_dma && !--pending_dma){
  if(fail_dma)hw_dma[1]=1;
  else{
   assert(hw_dma[0x1c/4]==2 && hw_dma[0x34/4]==2);
   assert(hw_dma[0x44/4]==(480u<<16|320));
   assert(hw_dma[0x10/4]==0 && hw_dma[0x40/4]==0);
   memcpy(frame_memory(hw_dma[0x3c/4]),frame_memory(hw_dma[0x0c/4]),TX15_LCD_BYTES);
   hw_dma[1]=2;clones++;
  }
  hw_dma[0]=0;
 }
 return hw_dma[(a-0x52001000)/4];
}
static void frame_write(uint32_t a,uint32_t v){
 if(a==0x580244d4){assert((v&~16u)==(hw_clock&~16u));hw_clock=v;return;}
 if(a==0x5802447c){if(v&16){memset(hw_dma,0,sizeof hw_dma);pending_dma=0;}return;}
 if(a>=0x50001000 && a<0x50001140){
  assert(a==0x500010ac || a==0x50001024);
  if(a==0x50001024){assert(v==2);pending_swap=20;}
  hw_ltdc[(a-0x50001000)/4]=v;return;
 }
 assert(a>=0x52001000 && a<0x52001060);
 if(a==0x52001008){hw_dma[1]&=~v;return;}
 hw_dma[(a-0x52001000)/4]=v;
 if(a==0x52001000 && (v&1))pending_dma=20;
}
#define TX15_FRAME_READ(a) frame_read(a)
#define TX15_FRAME_WRITE(a,v) frame_write(a,v)
#define TX15_FRAME_MEMORY(a) frame_memory(a)
#define TX15_FRAME_CYCLES() frame_cycles()
#define TX15_FRAME_BARRIER() ((void)0)
#include "src/target/tx/radiomaster/tx15/frame_swap.c"
static void frame_service(void){
 serviced++;
 uint32_t front=scan_address;
 tx15_frame_present(); /* Recursive commit must not change ownership. */
 assert(scan_address==front);
}
static void setup(void){
 hw_ltdc[0x18/4]=0x10012221;hw_ltdc[0xac/4]=TX15_LCD_FB;
 hw_ltdc[0x94/4]=2;hw_ltdc[0xb0/4]=(640u<<16)|647;hw_ltdc[0xb4/4]=480;
 for(unsigned i=0;i<TX15_LCD_BYTES/4;i++)frame_a[i]=0x12341234;
 tx15_frame_set_service(frame_service);assert(tx15_frame_init()==0);
 assert(!memcmp(frame_a,frame_b,sizeof frame_a));
}
static uint16_t at(uint32_t a,unsigned x,unsigned y){return ((uint16_t*)frame_memory(a))[y*480+x];}
'''

class FrameSwapTests(unittest.TestCase):
    run_c = switches.SwitchUpgradeTests.run_c

    def test_real_board_lcd_and_lua_callbacks_commit_only_at_run_boundary(self):
        self.run_c(HARDWARE+r'''
#define TX15_ELRS_LUA 1
#define TX15_ELRS_PRODUCT 1
#include "common.h"
#include "config/display.h"
#define TX15_DISPLAY_BARRIER() ((void)0)
#include "hardware/tx15/board/display.c"
#include "src/target/tx/radiomaster/tx15/lcd.c"
#include "src/target/tx/radiomaster/tx15/lua_tool.c"
struct display_settings Display;
static uint16_t font_color;
static unsigned fake_ms,run_count,hardware_polls;
u32 CLOCK_getms(void){return fake_ms+=20;}
void CLOCK_ResetWatchdog(void){}
int tx15_runtime_poll(unsigned ms){(void)ms;hardware_polls++;return 1;}
u8 LCD_SetFont(unsigned f){(void)f;return 1;}
void LCD_SetFontColor(u16 c){font_color=c;}
void LCD_GetStringDimensions(const u8 *s,u16 *w,u16 *h){*w=strlen((const char*)s)*6;*h=12;}
void LCD_PrintStringXY(unsigned x,unsigned y,const char *s){
 for(unsigned row=y;row<y+12;row++)for(unsigned col=x;col<x+strlen(s)*6;col++)
  LCD_DrawPixelXY(col,row,font_color);
}
void MIXER_CalcChannels(void){}
void BUTTON_Handler(void){}
void BUTTON_RegisterCallback(buttonAction_t *a,u32 b,unsigned f,
 unsigned (*cb)(u32,unsigned,void*),void *d){(void)a;(void)b;(void)f;(void)cb;(void)d;}
void BUTTON_UnregisterCallback(buttonAction_t *a){(void)a;}
const char *tx15_rf_lua_error(void){return "";}
void tx15_rf_lua_stop(void){}
struct crsf_link *tx15_rf_lua_init(void){return NULL;}
int tx15_rf_lua_authorize(uint8_t t,const uint8_t *p,unsigned n){(void)t;(void)p;(void)n;return 1;}
int tx15_rf_lua_writes_enabled(void){return 1;}
static const uint8_t dummy_script[]={0};
const struct tx15_resource tx15_resources[]={{"scripts/elrs.lua",dummy_script,1}};
const size_t tx15_resource_count=1;
int nd_lua_start(struct nd_lua *l,void *a,size_t n,const struct nd_lua_host *h,
 struct crsf_link *link,const char *s,size_t bytes){
 (void)a;(void)n;(void)link;(void)s;assert(bytes==1);l->host=*h;l->state=ND_LUA_RUNNING;return 0;
}
int nd_lua_run(struct nd_lua *l,int event){
 (void)event;assert(swaps==run_count);run_count++;
 uint32_t old=scan_address;uint16_t old_pixel=at(old,5,6);
 l->host.clear(NULL);
 l->host.text(NULL,5,6,"ELRS",0,0xf800+run_count);
 l->host.rect(NULL,-2,-2,5,5,0x07e0,1);
 l->host.line(NULL,100,100,105,105,0x001f);
 assert(scan_address==old && at(old,5,6)==old_pixel);
 if(run_count==2)l->state=ND_LUA_EXITED;
 return 0;
}
void nd_lua_close(struct nd_lua *l){(void)l;}
void GUI_DrawScreen(void){
 assert(run_count==2 && swaps==2 && at(scan_address,5,6)==0xf802);
 assert(at(scan_address,0,0)==0x07e0 && at(scan_address,105,105)==0x001f);
 LCD_DrawStart(0,0,0,0,DRAW_NWSE);LCD_DrawPixel(0xabcd);LCD_DrawStop();
 assert(at(scan_address,0,0)==0x07e0);
 LCD_ForceUpdate();assert(swaps==3 && at(scan_address,0,0)==0xabcd);
}
int main(void){
 setup();tx15_lua_tool();assert(swaps==3 && hardware_polls>0);return 0;
}''',[])

    def test_hidden_frame_swap_retention_and_no_empty_commit(self):
        self.run_c(HARDWARE+r'''
int main(void){
 setup();unsigned copied=clones;assert(copied==1);
 tx15_frame_present();assert(!swaps && clones==copied);
 tx15_frame_rect(0,0,480,320,0xffff);
 tx15_frame_pixel(15,30,0xf800);
 assert(scan_address==TX15_LCD_FB && at(scan_address,15,30)==0x1234);
 assert(at(tx15_frame_draw_address(),15,30)==0xf800);
 tx15_frame_present();assert(scan_address==0xd0100000 && swaps==1);
 assert(at(scan_address,15,30)==0xf800 && at(scan_address,14,30)==0xffff);
 assert(!memcmp(frame_a,frame_b,sizeof frame_a));
 tx15_frame_pixel(479,319,0x9876);tx15_frame_pixel(480,320,1);
 tx15_frame_present();assert(scan_address==TX15_LCD_FB && swaps==2);
 assert(at(scan_address,479,319)==0x9876 && at(scan_address,15,30)==0xf800);
 tx15_frame_rect(479,319,~0u,~0u,0x2222);tx15_frame_present();
 assert(at(scan_address,479,319)==0x2222 && at(scan_address,478,319)==0xffff);
 assert(serviced>0 && tx15_frame_report.frames==3);
 assert(tx15_frame_report.max_wait_cycles && tx15_frame_report.max_copy_cycles);
 return 0;
}''',[])

    def test_reload_timeout_never_reuses_pending_frame(self):
        self.run_c(HARDWARE+r'''
int main(void){
 setup();tx15_frame_pixel(10,20,0xabcd);hold_swap=1;
 unsigned before=clones;tx15_frame_present();
 assert(!tx15_frame_ready() && tx15_frame_report.swap_timeouts==1);
 assert(clones==before && scan_address==TX15_LCD_FB && serviced>0);
 uint32_t hidden=tx15_frame_draw_address();assert(at(hidden,10,20)==0xabcd);
 tx15_frame_pixel(10,20,0x5555);tx15_frame_rect(0,0,480,320,0);
 assert(at(hidden,10,20)==0xabcd); /* requested frame remains immutable */
 hold_swap=0;while(pending_swap)frame_read(0x50001024);
 assert(at(scan_address,10,20)==0xabcd);
 tx15_frame_present();assert(clones==before);
 return 0;
}''',[])

    def test_stopped_cycle_counter_still_has_finite_reload_budget(self):
        self.run_c(HARDWARE.replace('cycles_fake+=12800;return cycles_fake;',
                                   'return cycles_fake;')+r'''
int main(void){
 setup();tx15_frame_pixel(10,20,0xabcd);hold_swap=1;
 tx15_frame_present();
 assert(!tx15_frame_ready() && tx15_frame_report.swap_timeouts==1);
 assert(scan_address==TX15_LCD_FB && at(TX15_FRAME_BACK,10,20)==0xabcd);
 return 0;
}''',[])

    def test_unknown_scan_configuration_is_not_reprogrammed(self):
        self.run_c(HARDWARE+r'''
int main(void){
 hw_ltdc[0x18/4]=0x10012221;hw_ltdc[0xac/4]=TX15_LCD_FB;
 hw_ltdc[0x94/4]=2;hw_ltdc[0xb0/4]=(960u<<16)|967;hw_ltdc[0xb4/4]=320;
 assert(tx15_frame_init()!=0 && !tx15_frame_ready());
 tx15_frame_pixel(0,0,0xffff);tx15_frame_present();
 assert(hw_ltdc[0xb0/4]==((960u<<16)|967) && !frame_a[0] && !frame_b[0]);
 assert(!clones && !swaps);return 0;
}''',[])

    def test_power_modal_present_and_cancel_restore_after_buffer_exchange(self):
        self.run_c(HARDWARE+r'''
#define TX15_STANDALONE 1
#include "common.h"
static uint16_t ui_saved[360*192];
static uint32_t ui_ms,ui_started,ui_duration;
static unsigned ui_seen,ui_shutdown,ui_guard;
static volatile uint16_t *ui_memory(uint32_t a){
 if(a==0xd0200000)return ui_saved;
 return (volatile uint16_t*)frame_memory(a);
}
#define TX15_POWER_UI_MEMORY(a) ui_memory(a)
#include "src/target/tx/radiomaster/tx15/power_ui.c"
u32 CLOCK_getms(void){return ui_ms;}
uint32_t tx15_power_status(void){return ui_ms-ui_started<ui_duration?TX15_BUTTON_PRESSED:0;}
int tx15_runtime_poll(unsigned t){
 (void)t;ui_ms++;
 if(at(scan_address,60,64)==0xfd20)ui_seen++;
 if(!ui_guard){ui_guard=1;tx15_power_ui_poll();ui_guard=0;}
 return 1;
}
void PWR_Shutdown(void){ui_shutdown++;}
static void ui_service(void){tx15_runtime_poll(ui_ms);}
int main(void){
 setup();tx15_frame_pixel(0,0,0x5678);tx15_frame_present();
 static uint32_t original[TX15_LCD_BYTES/4];memcpy(original,frame_a,sizeof original);
 tx15_frame_set_service(ui_service);
 tx15_power_ui_poll();ui_ms+=20;tx15_power_ui_poll();
 ui_started=ui_ms;ui_duration=600;tx15_power_ui_poll();
 assert(swaps>1 && ui_seen && !ui_shutdown);
 assert(!memcmp(frame_a,original,sizeof original) && !memcmp(frame_b,original,sizeof original));
 ui_started=ui_ms;ui_duration=~0u;tx15_power_ui_poll();
 assert(ui_shutdown==1 && ui_ms-ui_started>=2000);
 assert(at(scan_address,90,190)==0xfd20);
 return 0;
}''',['hardware/tx15/boot/power_button.c'])

    def test_dma_error_and_stall_reset_before_serviced_cpu_recovery(self):
        for mode in ('fail_dma','hang_dma'):
            with self.subTest(mode=mode):
                self.run_c(HARDWARE+r'''
int main(void){
 setup();FAIL=1;tx15_frame_pixel(22,33,0xeeee);tx15_frame_present();
 assert(tx15_frame_ready() && tx15_frame_report.dma_errors==1);
 assert(tx15_frame_report.cpu_copies==1 && !pending_dma && !(hw_dma[0]&1));
 assert(!memcmp(frame_a,frame_b,sizeof frame_a));
 tx15_frame_pixel(23,33,0x9999);tx15_frame_present();
 assert(tx15_frame_report.dma_errors==1 && tx15_frame_report.cpu_copies==2);
 assert(at(scan_address,22,33)==0xeeee && at(scan_address,23,33)==0x9999);
 assert(serviced>0);return 0;
}'''.replace('FAIL',mode),[])
