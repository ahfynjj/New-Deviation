# TX15 MAX native audio A0

Updated2026-10-18 AUD3. User reports AUD2 emits a tone but remains very quiet at maximum5.
Basic synthesized sound is confirmed; loudness is not accepted. No EdgeTX scheduler, mixer or audio framework is linked.

## Ownership and memory

| Region | Owner | Initialization |
|---|---|---|
| AXI 0x24000000..0x24010000 | existing loader/report | unchanged |
| AXI 0x24010000..0x2407c000 | application code/data | existing loader/BSS |
| AXI 0x2407c000..0x24080000 | 16 KiB stack | existing startup |
| D2 0x30000000..0x30028000 | existing 160 KiB Lua arena, moved intact | audio_memory_init before any Lua access |
| D2 0x30028000..0x3002c000 | 16 KiB PCM reservation; A0 uses first 4 KiB for prepared blocks | explicit zero |
| D2 0x3002c000..0x3002d000 | two 2 KiB DMA blocks | explicit zero, 32-byte aligned |
| D2 0x3002d000..0x30030000 | 12 KiB reserved for later queue/parser | explicit zero |
| D2 0x30030000..0x30048000 | unallocated | not accessed |
| SDRAM 0xd0000000..0xd004b000 | existing 480x320 RGB565 framebuffer | unchanged |
| SDRAM 0xd0080000..0xd0100000 | existing embedded resources | unchanged |

Existing RF parameter cache (~32 KiB), libc arena (16 KiB), USB/app settings and model/calibration records stay in their existing regions. No new ELF load segment is emitted, no loader address whitelist changes, and no stack reduction. D2 SRAM1/2 clocks are enabled/read back before clearing the owned 192 KiB. Caches/MPU must remain off per native loader contract; reject use otherwise. Default audio-off builds keep the original AXI Lua arena. Hardware address accessibility and Lua operation after migration are not proven by host tests.

## Hardware and clocks

- TAS2505 at 7-bit 0x18, reset PH10. Only speaker output in A0; headphone/Bluetooth/input pins are not configured.
- I2S2/SPI2 AF5: PC6 MCLK, PI0 WS, PI1 BCLK, PI3 SDO. DMA1 Stream4, DMAMUX1 channel4 request40, IRQ15. SPI2 TXDR 16-bit transfers, two 512-frame stereo blocks (16 ms each).
- PLL1/system clocks and LCD PLL3 remain untouched. Fixed media PLL2: HSE48/M12*(98+2490/8192)/P8 =49.1519775 MHz, and /R2=196.60791MHz for SDMMC. Configure both output gates while PLL2 is off, after NOR model/calibration restore; keep it on across audio/storage exit. SPI123 selects PLL2P; I2S divides by6, MCLK≈8.192 MHz, Fs≈31999.985 Hz. These rates are calculated, not measured. Future SPI1/3 users must coordinate the shared selector.
- Codec uses MCLK directly with NDAC2, MDAC1, DOSR128, PRB_P3/RC4; 16-bit Philips I2S, left channel. Reference stabilization waits45ms, DAC soft-step waits10ms without blocking.
- AUD3 defaults3/5: DAC-6dB, speaker amplifier+6dB, speaker attenuation about12dB (register46=24); synthetic peak8192/32768 unchanged. Levels1..5 use72/48/24/12/0; max5 removes the previous about20dB extra attenuation. Volume0 explicitly mutes the speaker amplifier. No automatic event or persisted volume is added. Actual sound pressure/distortion remain unmeasured.

I2C4/PD12,PD13 remains owned by controls.c. Codec requests use that driver's lock, only address0x18, one register operation per main-loop poll, actual128000-cycle/1ms deadline at fixed128MHz and finite loop cap. Unlike old tick subtraction, crossing a millisecond boundary does not expire a sub-ms transfer. DWT TRCENA/LSR/LAR/CYCCNTENA are prepared without resetting CYCCNT; the counter remains available to diagnostics. I2CFFFFFFFE means cycle timer unavailable, not a hardware ISR. No codec access in IRQ. NACK requests STOP and clears transfer flags; it does not reset I2C4 or PG10 expanders. Normal input recovery remains unchanged. The pre-existing input fault recovery can still reset the bus when the inputs themselves fail. A stuck shared wire can affect both clients; A0 does not claim physical fault immunity.

DMA IRQ only copies a prepared block to the inactive half, or fills silence and counts underruns; generation/I2C stays in the main loop. DMA errors stop SPI and assert codec reset, then main-loop cleanup changes status to Error. Poll/IRQ cycle cost and RF interval remain hardware acceptance items. A0 emits a faded 1kHz triangle for300ms; this is a synthesized diagnostic, not WAV or a speech test.

## Sources

- [ST STM32H750 device definitions](https://github.com/STMicroelectronics/cmsis-device-h7/blob/master/Include/stm32h750xx.h), local `local/references/stm32h750xx.h`; register positions checked against this downloaded header.
- [ST HAL I2S v1.11.2](https://github.com/STMicroelectronics/stm32h7xx-hal-driver/blob/v1.11.2/Src/stm32h7xx_hal_i2s.c): Philips I2S master transmit and DMA/enable sequence.
- [TI TAS2505 datasheet](https://www.ti.com/lit/ds/symlink/tas2505.pdf) and [SLAU472 application guide](https://www.ti.com/lit/ug/slau472/slau472.pdf): clock/processing constraints, register map and power sequencing. Guide downloaded 2026-10-16 reports revisionD.
- [Fixed TX15 pin reference](https://github.com/EdgeTX/edgetx/blob/f5c13ab13ecadf3689c5854cfba51c43646fceec/radio/src/targets/tx15/hal.h), [fixed rm-h750 audio reference](https://github.com/EdgeTX/edgetx/blob/f5c13ab13ecadf3689c5854cfba51c43646fceec/radio/src/boards/rm-h750/audio_driver.cpp): hardware connections only; independent register-level implementation based on chip documentation.
