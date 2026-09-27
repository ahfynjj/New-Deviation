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

Status: cross-build and 16 hardware-tool tests passed during implementation.
The earlier V2 native-power board evidence remains valid for that image only.
The 2026-09-27 15:58 bench attempt timed out waiting for the button; no reset or
target writes occurred. Do not interpret the compiled V3 image as board proof.

At 16:08 a new V3 board run succeeded: RCC_CR=0x34025, RCC_CFGR=0x12,
D1CFGR=0; ticks 263->588 and loops 80830->180053, power_status=15 and no
reported faults. Recovery read back HSI CR=0x4025/CFGR=0/D1CFGR=0 before
restoring CPU context. Original firmware resumed and the user confirmed the
screen normal. See `docs/tx15/evidence/2026-09-27/hse-clock/`. This verifies
direct HSE execution on this board, not calibrated frequency or PLL operation.

## PLL128 stage (V4)

The next bounded profile is HSE48 / M12 * N64 / P2 = 128 MHz CPU,
AHB /2 = 64 MHz, APB1..4 /2 = 32 MHz. VCO is 256 MHz, wide range;
PLL1RGE=2 selects the 4..8 MHz input band, FRACEN=0, only P output enabled.
The profile does not change the voltage or Flash configuration. It requires
ACTVOSRDY, a nonzero ACTVOS code, LDO enabled without bypass, and an existing
Flash latency of 1..7. This covers the 64 MHz AXI clock even in VOS3.

References checked: ST [RM0433 rev 8](https://www.st.com/resource/en/reference_manual/rm0433-stm32h742-stm32h743-753-and-stm32h750-value-line-advanced-armbased-32bit-mcus-stmicroelectronics.pdf)
(Table 17 and PLL initialization/register definitions),
[DS12556 rev 8](https://www.st.com/resource/en/datasheet/stm32h750vb.pdf)
(rev V electrical clock limits), and the
[H750 CMSIS header](https://github.com/STMicroelectronics/cmsis-device-h7/blob/master/Include/stm32h750xx.h).
The 128/64/32 profile stays below VOS3 clock maxima. It is a bring-up profile,
not the final production clock tree; USB/display/ADC clocks are not configured.

Driver order: require direct HSE state -> program/read back PLL factors while
disabled -> enable/wait lock -> install/read back bus dividers -> select/wait PLL.
V4 keeps the 80-byte mailbox. Additional host register snapshots verify the PLL
factors, all APB dividers and unchanged PWR/Flash state alongside both mailboxes.

Recovery saves reset-entry RCC settings before loading RAM. With CPU halted and
SysTick off, select/confirm HSI, disable/wait PLL1, restore PLL factors and bus
dividers, disable/wait HSE, then require exact RCC readback before CPU restoration.
Any recovery error prevents the original reset handler from being resumed.

V4 implementation: text=2140 bytes, RAM load padded to 2144; 20 host checks pass.
ELF SHA256: `b28741424393788792c64f402d62a20eba02f60bed728140fe42c49883e273d3`.
BIN SHA256: `aa739f74070a94978e116b21e6bd41c3b55da681d66d0d02f4d46b6ed379f894`.
At 20:50 the V4 board run passed. Both full PLL/divider snapshots match this
profile; ticks 264->599, loops 140284->317452, power_status=15, no reported faults.
Reset-entry PWR_CSR1/D3CR=0x6000, PWR_CR3=0x05000042 and FLASH_ACR=0x37
remained unchanged throughout the diagnostic. All saved RCC registers restored
exactly before CPU recovery; no recovery errors. The user confirmed normal
screen after original firmware resumed. Evidence: `docs/tx15/evidence/2026-09-27/pll128/`.
This establishes the tested warm-reset profile; no calibrated frequency or cold
power-on claim, and no external-memory/peripheral kernel clocks configured yet.
