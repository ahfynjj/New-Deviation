# TX15 Hardware Bring-up Implementation Plan

**Goal:** Move all new development to TX15 MAX hardware, beginning with a real
STM32H750 RAM-resident diagnostic image and a reproducible debugger workflow.
**Architecture:** Native Deviation remains the product. The separate bare-metal
bring-up image verifies MCU execution before board-specific drivers are enabled.
It is not a simulator and not the complete Deviation application.
**Tech Stack:** GNU Arm GCC, Cortex-M7 assembly/C, ST RM0433/DS12556, ST-Link/SWD.
**Spec:** `../specs/2026-09-21-tx15-native-design.md`, overridden by the user's
2026-09-23 instruction to stop simulator development and focus on hardware.

## Scope and constraints

- Freeze simulator features and interactive acceptance as development priorities.
- No further dependency on other transmitter firmware or its version.
- Use ST documentation for MCU facts. Board identity and SWD/power must be checked
  on the user's unit before executing the image. USB inventory found no matching
  ST-Link/STM32 device at the start of this increment.
- Build a RAM image at documented AXI SRAM addresses; no flash image/eraser or
  guessed board GPIOs. Code runs after a verified reset-halt state, not as a
  chainloaded extension of an existing application.
- No MCU power-hold, LCD, external memory, RF or ADC claim from a successful build.

## Task 1: Hardware diagnostic image

Create `hardware/tx15/ram_probe/{startup.S,probe.c,probe.h,ram.ld}` and
`utils/build-tx15-hardware.ps1`. Link code/data/BSS, a fixed diagnostic mailbox,
and stack inside the first 64 KiB of AXI SRAM. Record chip/core/clock state,
verify a dedicated scratch RAM buffer, then run SysTick and main-loop counters.
Reject unsupported clock/cache/MPU state. Capture fault register evidence.

Tests first: validate ELF entry/vector/segments, mailbox/stack separation and
absence of flash load addresses. Compile target C/assembly with warnings as
errors; inspect generated code for startup and vector correctness.

## Task 2: Debug evidence workflow

Provide a host decoder for debugger-read mailbox dumps, with malformed input,
failed state, zero/stale ticks and wraparound tests. Document reset-state/power
requirements and readback fields without inventing SWD pads or automating writes
to an unidentified device. A generated ELF is ready for bench verification only.

## Task 3: Handoff and next hardware stages

Update project priorities, hardware records and continuation commands. Review
the complete increment, fix actionable issues, verify, commit and sync branch.
Next: actual SWD identity/reset/RAM run evidence, confirmed power control, external
memory, display/touch, ADC/switches, and finally CRSF/ELRS hardware integration.

## Review focus

RAM load ranges, stack/mailbox overlap, reset assumptions, clock timing claims,
uninitialized RAM/ECC, interrupt vectors, debugger state and misleading success
from stale mailbox contents. Do not grade compilation as physical execution.
