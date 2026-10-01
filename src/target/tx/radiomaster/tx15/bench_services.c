/* Explicit P2 bench-only services; GPL-3.0-or-later.
 * RF/USB/trainer/audio are unavailable; no peripheral writes here.
 * This is not a flight-capable build. Analog inputs are implemented separately; ELRS follows in P4.
 */
#include "common.h"
#include "mixer.h"
#include "config/model.h"
#include "config/tx.h"
#include "music.h"
volatile u8 priority_ready;
volatile s32 ppmChannels[MAX_PPM_IN_CHANNELS];
volatile u8 ppmSync;
const u8 EATRG0[PROTO_MAP_LEN]={INP_ELEVATOR,INP_AILERON,INP_THROTTLE,INP_RUDDER,INP_GEAR1};
const u8 *CurrentProtocolChannelMap=EATRG0;
void MCU_InitModules(void) { memset(Transmitter.module_enable,0,sizeof(Transmitter.module_enable)); }
int MCU_SetPin(struct mcu_pin *p,const char *name) { (void)p;(void)name;return 0; }
unsigned PWR_ReadVoltage(void) { return 0; } /* Unmeasured, not a fabricated battery voltage. */
int PWR_CheckPowerSwitch(void) { return 0; }
void PWR_Shutdown(void) { for(;;) __asm volatile("nop"); }
int SPITouch_IRQ(void) { return 0; }
void CLOCK_ResetWatchdog(void) {}
void BACKLIGHT_Brightness(unsigned b) { (void)b; } /* bootstrap owns backlight */
void PPMin_Start(void) {} void PPMin_Stop(void) {}
void MSC_Enable(void) {} void MSC_Disable(void) {}
void SOUND_SetFrequency(unsigned f,unsigned v) { (void)f;(void)v; }
void SOUND_StartWithoutVibrating(unsigned ms,u16(*cb)(void)) { (void)ms;(void)cb; }
void MUSIC_Play(u16 m) { (void)m; }
void PROTOCOL_Init(u8 force) { (void)force;Model.protocol=PROTOCOL_NONE; }
void PROTOCOL_Load(int dialog) { (void)dialog;Model.protocol=PROTOCOL_NONE; }
void PROTOCOL_DeInit(void) {}
u8 PROTOCOL_AutoBindEnabled(void) { return 0; }
void PROTOCOL_Bind(void) {}
u32 PROTOCOL_Binding(void) { return 0; }
void PROTOCOL_ChangedID(void) {}
u64 PROTOCOL_CheckSafe(void) { return 0; }
u32 PROTOCOL_CurrentID(void) { return 0; }
u32 PROTOCOL_MaximumID(void) { return 0; }
int PROTOCOL_DefaultNumChannels(void) { return 4; }
int PROTOCOL_NumChannels(void) { return 4; }
const char *PROTOCOL_GetName(u16 p) { return p?"Unavailable":"None"; }
const char *PROTOCOL_Name(void) { return "None"; }
const char **PROTOCOL_GetOptions(void) { return NULL; }
enum Radio PROTOCOL_GetRadio(u16 p) { (void)p;return CYRF6936; }
int PROTOCOL_GetTelemetryState(void) { return 0; }
int PROTOCOL_GetTelemetryType(void) { return 0; }
int PROTOCOL_HasModule(int p) { return p==PROTOCOL_NONE; }
int PROTOCOL_HasPowerAmp(int p) { (void)p;return 0; }
int PROTOCOL_MapChannel(int input,int fallback) { (void)input;return fallback; }
int PROTOCOL_OptionsPage(void) { return 0; }
int PROTOCOL_RangeTest(int on) { (void)on;return 0; }
void PROTOCOL_SetOptions(void) {}

void PROTOCOL_ResetTelemetry(void) {}
