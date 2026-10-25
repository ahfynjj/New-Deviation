# TX15 global frame presentation implementation plan

**Goal:** Hide intermediate erase/draw states across native GUI and ELRS Lua,
while preserving RF servicing, settings, bootloader and acceptable input latency.

**Evidence:** RD01 changes only bounded labels. lua_tool.c clear/fill writes the
visible framebuffer, and Lua requests no presentation in direct mode. GUI
LCD_ForceUpdate is also empty. AV03's pixel comparisons, dirty rectangle copy
and per-512-pixel watchdog calls caused user-visible lag and remain disabled.

**Architecture:** Two RGB565 framebuffers: D0000000 and expired loader staging
D0100000, each 307200 bytes. All application drawing uses the hidden buffer.
LCD_ForceUpdate changes LTDC layer1 address with vertical-blank reload, waits
with bounded hardware-only services for acknowledgment, then DMA2D clones the
completed visible frame into the now-hidden buffer to preserve partial GUI
updates. No pixel comparison, CPU dirty-region scan or normal CPU full-frame
copy. Audio's changed-row cache remains. Short-label compositor is disabled
in this mode because a whole frame is already hidden. Build is opt-in RD02.

**Reference:** STM32H750 CMSIS register definitions and STM32H7 HAL LTDC/DMA2D
drivers, checked 2026-10-25. Native code only; no HAL runtime dependency.

## Constraints and failure handling

- Standalone application only, after boot staging is expired; no BL update.
- Preserve original 320x480 LTDC scan configuration and linear landscape data.
- Cache/MPU remain off, so CPU, DMA2D and LTDC see the same SDRAM contents.
- DMA2D is exclusively owned here; no DMA1/audio or SDMMC changes.
- Never draw into a requested/visible frame until reload is acknowledged.
- Reload timeout freezes display writes; services and power-off continue.
- DMA error/timeout resets only DMA2D before bounded serviced word-copy recovery;
  subsequent copies use recovery mode. Record faults and timing maxima.
- Modal power UI must use the same hidden target and present completed steps;
  cancellation restores exact saved pixels and continues caller state.

## Implementation and checks

- [x] Add failing C tests for hidden clear/text/line, empty commit, acknowledged
  swaps, alternating buffers, retained partial updates, service/reentry,
  no premature reuse, VBR timeout and DMA failure recovery.
- [x] Implement frame_swap.c/.h with test seams, DWT deadlines, DMA2D RGB565 M2M,
  and LTDC VBR. Use real board pixel and LCD adapter paths in regression tests.
- [x] Route Lua fill/line/text and each run/error frame through presentation;
  test the actual Lua callbacks and run loop completion boundary.
- [x] Route shutdown modal capture/draw/restore through the active back buffer;
  retain exact cancellation and continuous services in existing and new tests.
- [x] Build ARM application, validate final ELF and NDU ABI/CRC/load layout;
  independently review buffer ownership, timeouts, RF and modal interactions.
- [x] Prepare USB-only candidate and preserve RD01 for rollback. Hardware
  acceptance requires Lua and normal menu visual/latency checks plus ELRS
  continuity. Host tests do not establish physical timing or flicker removal.

## Result and update procedure

25 focused tests passed, including the real board drawing functions, LCD
adapter, Lua tool run loop, modal cancellation after buffer exchange,
DMA error/stall recovery, pending-frame immutability, a stopped cycle counter
and unsupported scan configuration. The first Lua integration test failed
against the visible-frame drawing path; the power-modal test failed before
its dynamic-buffer/presentation integration. Both passed after implementation.
152 ARM objects built and linked, including the official Lua runtime. Existing
vendor/legacy warnings remain; the new frame module emitted no warnings.
Independent review checked register layouts and ownership and found no
important blocker. No hardware was accessed and no Flash written.

Package: `local/tx15-usb-release/tx15-frame-swap-rd02-20261025.ndu`,
711096 bytes, SHA256
`d381f8e21f80e287cb9b3f44f5c026f51ec516a47c30d377b59cd668f69c71f2`.
The validated header and ND15 payload retain Boot API 1 / settings ABI 1.
The ELF contains frame presentation and power UI; the older software buffer
and short-label compositor are not linked. Build and package evidence:
`evidence/2026-10-25/frame-swap-candidate.json`.

Build with `TX15_FRAME_SWAP=1`, `TX15_BUFFERED_DISPLAY=0`,
`TX15_STATUS_REGIONS=0` and the existing standalone ELRS product, Lua writes,
persistence, audio and storage flags. No bootloader or settings-layout change.

Enter USB UPDATE with EXIT+power, select this NDU in the dedicated updater,
then restart. About must show RD02; Audio retains AUD4 and its idle-row cache.
Check ordinary menu selection, input monitor bars, and ELRS Lua lists/folders
with changing values. Confirm responsiveness and a continuous receiver link
for at least one minute, then cancel a shutdown hold and confirm the same
page returns. These visual, latency and RF checks remain pending. A dirty
commit waits up to one refresh and clones one full frame; actual target timing
and bus contention have not been established by the host tests. RD01 remains
available at `local/tx15-usb-release/tx15-status-redraw-20261025.ndu` for USB
rollback if the new rendering is slower or otherwise incorrect.

Primary register references:
[ST STM32H750 CMSIS](https://github.com/STMicroelectronics/cmsis-device-h7/blob/master/Include/stm32h750xx.h),
[ST LTDC driver](https://github.com/STMicroelectronics/stm32h7xx-hal-driver/blob/master/Src/stm32h7xx_hal_ltdc.c),
[ST DMA2D driver](https://github.com/STMicroelectronics/stm32h7xx-hal-driver/blob/master/Src/stm32h7xx_hal_dma2d.c).
