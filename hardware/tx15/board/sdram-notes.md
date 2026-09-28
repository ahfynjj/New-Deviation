# TX15 SDRAM first bring-up (V5)

Scope: native Deviation board driver, warm-reset RAM diagnostic. No Flash or
option-byte writes. Test only `0xd0000000..0xd000ffff` (64 KiB of volatile RAM).
No LCD, full-capacity, retention-duration, cold-start or production-readiness claim.

The 2026-09-27 running-board readback (`local/identity-20260927-205522.json`)
matched the reference SDRAM pin routing and SDCR2=0x1d4: bank2, 16-bit width,
12 row bits, 8 column bits, 4 internal banks. This describes an 8 MiB mapping;
the exact chip marking remains unknown. The bench loader checks geometry and
every listed GPIO's alternate-function configuration before resetting the board.

| Port | FMC AF12 pins |
|---|---|
| C | 0 |
| D | 0, 1, 8, 9, 10, 14, 15 |
| E | 0, 1, 7–15 |
| F | 0–5, 11–15 |
| G | 0, 1, 4, 5, 8, 15 |
| H | 6, 7 |

Reference: local EdgeTX `radio/src/boards/rm-h750/sdram_driver.cpp`, used for
board facts. Native code preserves unrelated pins, particularly PH12 power hold.
ST's [H7 FMC implementation](https://github.com/STMicroelectronics/stm32h7xx-hal-driver/blob/master/Src/stm32h7xx_ll_fmc.c)
and [H750 register header](https://github.com/STMicroelectronics/cmsis-device-h7/blob/master/Include/stm32h750xx.h)
were checked for shared bank1 timing fields and command encoding. Unlike some
older STM32 series, H750 SDSR has no BUSY flag; no invented BUSY polling is used.

Use the validated PLL128/AHB64 profile, FMC kernel=HCLK, SDRAM clock=32 MHz.
Timing cycles: TMRD=2, TXSR=8, TRAS=4, TRC=8, TWR=6, TRP=4, TRCD=4.
These are deliberately relaxed at this low clock, pending chip-specific timing
qualification. Shared TRC/TRP live in SDTR1 even for SDRAM bank2.
CL3, burst length2, single writes; clock-enable, >=1 ms delay, precharge-all,
eight auto-refresh cycles, mode-load. Refresh count230 gives nominal 7.8125 us
including the controller's 20-cycle margin. The delay loop is a conservative
minimum-duration loop at the checked CPU clock, not a precision timer.

The diagnostic performs 32 walking-one checks at the base address and two
address-derived/inverted pattern passes over 16384 words: 32800 comparisons.
It records state, failure address/expected/actual values and FMC register readback.
V5 extends the mailbox from 80 to 128 bytes; historical V1–V4 dumps still decode.
Use only the V5-compatible loader; old 80-byte scripts are incompatible.

Recovery: halt CPU and stop SysTick, reset FMC, restore the saved FMC/GPIO
configuration and clock gates with readback, then restore PLL/HSI and original
CPU reset-entry context. SDRAM contents are not restored; the original reset
handler must initialize them afresh. Any recovery failure prevents resume.

Status on 2026-09-28: 24 host checks passed; ELF/BIN hash guard passed.
Independent review completed after fixing capture clock-restoration failure
handling: attempt both clocks independently, verify readback and prohibit CPU
resume on any cleanup failure. V5 first-64-KiB board execution passed at 20:30,
as detailed below.
The 2026-09-28 20:29 attempt timed out waiting for the button: no reset or target
writes were attempted (`local/reset-halt-power-20260928-202900.json`).
ELF SHA256 `dbbe54a38985867976f004e3a093d0b7f4a598431ee8db1bb0f121b8eab080f2`.
BIN SHA256 `528c0920510f913a38594210406248d1a2ee2cf0af7b0e2b5c1ba9c78415f494`.

## 2026-09-28 20:30 board result

A fresh button-assisted run passed: all 32800 comparisons over the bounded
64 KiB test completed, sdram_state=3/error=0/words=16384. Two V5 mailboxes show
ticks 221->570 and loops 121603->312231, power_status=15 and no recorded faults.
SDCR1=0x1ad0, SDCR2=0x1d4, SDTR1=0xf3f7fff, SDTR2=0x3050371, SDRTR=460.
FMC/GPIO and PLL/CPU recovery succeeded with no errors; PWR/Flash configuration
was unchanged. The user confirmed the original screen restored normally.
Evidence: `docs/tx15/evidence/2026-09-28/sdram64k/`.
This supersedes the earlier pending-run status only for the first 64 KiB test.
Full 8 MiB address coverage, retention and cold-start behavior remain unverified.
