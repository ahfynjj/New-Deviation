# TX15 MAX clock bring-up

The first native clock stage uses the external crystal directly at 48 MHz.
It does not configure PLLs, voltage scaling, Flash latency, SDRAM or peripheral
kernel clocks. HSI stays enabled so the bench loader can restore the reset-entry
clock before returning to the original firmware. No persistent storage is written.

Board frequency reference: EdgeTX TX15 `CMakeLists.txt`, `HSE_VALUE=48000000`,
in the local hardware reference checkout. The STM32H750 CMSIS register definitions
give HSEON/HSERDY at RCC_CR bits 16/17 and HSE selection SW=2, SWS=2
(RCC_CFGR low six bits 0x12). The driver is native register-level C.

- Require ready HSI64 with no core/AHB division and no active HSE, bypass, CSS or PLL.
- Enable HSE, wait for readiness, request source switch, confirm switch status.
- Bound both waits by a register-poll budget; this is not a calibrated timeout.
- Preserve unrelated register bits. Retain HSI on all outcomes.
- On failure stop the diagnostic with BAD_CLOCK. A timed-out switch can complete
  later, so the host must explicitly select HSI and confirm status before recovery.

Mailbox V3 keeps the 80-byte layout but records clocks **after** initialization.
SysTick uses a nominal 48000-cycle period. Two advancing snapshots plus HSE-ready,
HSE-selected and valid power flags establish execution; they do not measure
crystal accuracy. V1/V2 remain decodable as historical evidence.

`utils/hardware/reset_clock.py` is a restricted recovery helper for this stage.
Its caller must halt the core first, disable SysTick, keep PH12 high, wait for HSI,
select HSI, wait for SWS, disable HSE and confirm shutdown. Failed recovery must
leave the core halted and prohibit original-firmware resume.

Status: cross-build and 16 hardware-tool tests pass; V3 board execution pending.
The earlier V2 native-power board evidence remains valid for that image only.
The 2026-09-27 15:58 bench attempt timed out waiting for the button; no reset or
target writes occurred. Do not interpret the compiled V3 image as board proof.
