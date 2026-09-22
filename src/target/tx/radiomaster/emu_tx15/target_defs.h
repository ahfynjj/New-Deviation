#ifndef NEW_DEVIATION_TX15_EMU_TARGET_H
#define NEW_DEVIATION_TX15_EMU_TARGET_H

#ifndef EMULATOR
#error "emu_tx15 is a host simulator, not flashable TX15 firmware"
#endif
#include "target/drivers/mcu/emu/common_emu.h"
/* Shared data types used by protocol stubs; no physical pin map. */
#include "target/drivers/mcu/stm32/gpio.h"
#include "enable_native_fs.h"

#define TXID 0xF0  /* Host-only identity, not a hardware/DFU identifier. */
#define LCD_WIDTH 480
#define LCD_HEIGHT 320
#define ENABLE_320x240_GUI 1
#define HAS_STANDARD_GUI 1
#define HAS_ADVANCED_GUI 1
#define HAS_LAYOUT_EDITOR 1
#define HAS_PERMANENT_TIMER 1
#define HAS_TELEMETRY 1
#define HAS_EXTENDED_TELEMETRY 1
#define HAS_TOUCH 1
#define HAS_RTC 0
#define HAS_VIBRATINGMOTOR 0
#define HAS_DATALOG 1
#define SUPPORT_SCANNER 0
#define HAS_EXTRA_SWITCHES 0
#define HAS_EXTRA_BUTTONS 0
#define HAS_BUTTON_MATRIX_PULLUP 0
#define HAS_MULTIMOD_SUPPORT 0
#define HAS_VIDEO 0
#define HAS_4IN1_FLASH 0
#define HAS_EXTENDED_AUDIO 0
#define HAS_AUDIO_UART 0
#define HAS_MUSIC_CONFIG 0
#define HAS_OLED_DISPLAY 0
#define HAS_HARD_POWER_OFF 0
#define HAS_PWR_SWITCH_INVERTED 0
#define USE_4BUTTON_MODE 0
#define SUPPORT_STACKDUMP 0
#define DEBUG_WINDOW_SIZE 0
#define TXTYPE ""
#define FLASHTYPE FLASHTYPE_SPI
#define SPIFLASH_SECTORS 1024
#define SPIFLASH_SECTOR_OFFSET 0
#define MIN_BRIGHTNESS 1
#define DEFAULT_BATTERY_ALARM 7400
#define DEFAULT_BATTERY_CRITICAL 7000
#define MAX_BATTERY_ALARM 12000
#define MIN_BATTERY_ALARM 3300
#define MAX_POWER_ALARM 60
#define NUM_OUT_CHANNELS 16
#define NUM_VIRT_CHANNELS 10
#define NUM_TRIMS 10
#define MAX_POINTS 13
#define NUM_MIXERS ((NUM_OUT_CHANNELS + NUM_VIRT_CHANNELS) * 4)
#define INP_HAS_CALIBRATION 6
#define EMU_TARGET_INPUTS 1
#define STRICT_MODEL_INPUTS 1
#define STDMIXER_LAST_SWITCH INP_SWF0
#define CHANTEST_BUTTON_PLACEMENT { \
    {51, 120}, {51, 105}, {-229, 120}, {-229, 105}, \
    {-106, 135}, {21, 135}, {-259, 135}, {174, 135}, \
    {185, 220}, {185, 200}, {-95, 220}, {-95, 200}, {200, 180}, {-80, 180}, \
}

#endif
