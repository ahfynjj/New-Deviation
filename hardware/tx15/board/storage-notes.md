# TX15 internal storage S0 ownership

Updated2026-10-17 STO2. Native Deviation implementation; no EdgeTX runtime, HAL or filesystem imported.

The original S0 live PLL1Q gate assumption was incorrect. The STO1 photo shows
PLLCFGR01090898 (DIVQ1EN0) and CMD0/CPSMACT stuck. ST's
[LL RCC v1.11.2](https://github.com/STMicroelectronics/stm32h7xx-hal-driver/blob/v1.11.2/Inc/stm32h7xx_ll_rcc.h)
requires PLL1 disabled when enabling Q. The test previously failed to model this write protection.
Do not use the earlier PLL1Q notes as a valid implementation contract.

## Fixed reference and probe scope

The fixed EdgeTX commit `f5c13ab13ecadf3689c5854cfba51c43646fceec`
[TX15 HAL](https://github.com/EdgeTX/edgetx/blob/f5c13ab13ecadf3689c5854cfba51c43646fceec/radio/src/targets/tx15/hal.h)
selects SDMMC1. Its [shared SD driver](https://github.com/EdgeTX/edgetx/blob/f5c13ab13ecadf3689c5854cfba51c43646fceec/radio/src/targets/common/arm/stm32/diskio_sdio.cpp)
identifies SDMMC1 as internal and assigns PC8..11 (D0..3), PC12 (CLK), PD2 (CMD), AF12;
the other reader is SDMMC2/PH8. This establishes a pin/protocol candidate, not the identity or
capacity of the user's actual medium. Do not infer MMC/eMMC merely from "internal".

Register/response facts were checked against ST's official
[CMSIS STM32H750 definition](https://github.com/STMicroelectronics/cmsis-device-h7/blob/v1.10.3/Include/stm32h750xx.h),
[SD HAL](https://github.com/STMicroelectronics/stm32h7xx-hal-driver/blob/v1.11.2/Src/stm32h7xx_hal_sd.c),
[SDMMC LL](https://github.com/STMicroelectronics/stm32h7xx-hal-driver/blob/v1.11.2/Src/stm32h7xx_ll_sdmmc.c)
and [RCC extension HAL](https://github.com/STMicroelectronics/stm32h7xx-hal-driver/blob/v1.11.2/Src/stm32h7xx_hal_rcc_ex.c).
Read-only source copies are under `local/references/storage-s0` (CMSIS under `local/references`).
The implementation is independent MMIO C, using these only as hardware reference.

## Ownership

- `TX15_STORAGE=1` requires native standalone ELRS product and the audio D2 memory contract.
  It is opt-in; ordinary builds do not enable the controller.
- Manual MAIN MENU → Storage test → Scan only. No boot probe and no automatic retry.
- PLL1 and CPU128MHz remain untouched, including its output gates. Fixed application-owned
  PLL2 provides P49.15198MHz for audio and R196.60791MHz for SDMMC; both outputs are enabled
  while PLL2 is OFF. SDMMC divider246 gives399.61kHz. The clock is prepared after NOR restore
  and remains on across page exits; audio stop cannot remove storage clock. LCD retains PLL3.
  Scan preserves/restores only the SDMMC selector and its own peripheral/pin configuration.
- Refuse existing SDMMC1/2 use, SDMMC1 IRQ49 enabled, unexpected PLL1/clock profile,
  enabled MPU/caches or unsuitable DMA address. Require media clock ready or return HW2.
  Leave controller IRQ masked; do not wait for PLL lock in the storage driver.
- Use SDMMC1's own single-buffer IDMA, not DMA1/DMAMUX/audio stream. Private512B buffer
  aligned32 in DMA-accessible AXI SRAM; never in DTCM. Native caches/MPU remain disabled.
- Configure1-bit bus,3.3V, CMD/clock and data pins; save/restore only owned pin masks.
  GPIOC/D shared clocks remain on. Reset/power-down SDMMC1 and release its bus clock on exit.
- Scan success, error, deadline, Stop, page exit and shutdown all release the controller.
  Shutdown stops storage **before** the existing NOR model/calibration save. PLL1 stays
  compatible with the NOR guard throughout; ready PLL2 is already accepted by that guard.
  NOR layout and record format remain unchanged.

## Protocol and deadlines

CMD0/8 → CMD55/ACMD41 → CMD2/3/9 → CMD7/13 → CMD16 for SDSC only → CMD17
for sector0 and optionally the selected MBR partition boot sector. Command whitelist rejects
write/erase/bus-width/MMC commands. CMD17 always configures512B **receive**, not transmit.
No CMD24/25/32/33/38, no sector write API, no formatting, no model migration.

Only a CMD8 timeout permits SD-v1 fallback; invalid voltage echo/CRC/protocol fails closed.
R3 has no CRC; its CCRCFAIL is completion, not a generic waiver of response CRC checking.
Wait for CPSM idle before returning a successful response. Reads check R1, data CRC/timeout/
FIFO/IDMA errors, DATAEND, DCOUNT0 and controller idle before copying IDMA data.

Every main-loop call advances at most one command/state or copies one512B sector. No waiting
loops, filesystem calls or storage interrupts. Overall2s, command100ms, read250ms software
deadlines; the existing RF/input service remains in the loop. Real latency and RF coexistence
still require hardware acceptance; host tests do not prove them.

## Metadata only

CSD v1/v2 capacity, CID, OCR/RCA, sector0 signature, bounded MBR entries and FAT12/16/32 BPB
are decoded. Reject overlap, out-of-media ranges, inconsistent BPB and insufficient FAT
capacity. GPT/exFAT are reported unsupported; no following/mounting of either.
No directory listing, FAT-chain traversal, filesystem mounting or file reading exists yet.
Existing `romfs.c` is unchanged. Actual capacity, filesystem and SD protocol support are pending
the first STO0 hardware scan; errors do not justify trying writes or a different physical interface.
