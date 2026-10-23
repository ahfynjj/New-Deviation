# TX15 immediate boot acknowledgement (r3)

The user confirmed r2 shows POWER ON/LOADING and enters Deviation. Feedback
still appeared after a long blank interval. The required behavior is an
immediate visible acknowledgement, followed by screen progress, without
holding POWER blindly for several seconds.

## Implementation

The stackless reset supply function asserts PH12 power hold first, then lights
the blue status LED before any stack/RAM access, supply-ready loop, PLL,
SDRAM, or panel initialization. The user can release POWER when the blue light
is visible; the loader continues independently. This is an acknowledgement
of software entry, not a promise that every later initialization has succeeded.

The TX15 status LED pins are PI8 red, PI10 blue and PI11 green, active high.
Only those GPIOI mode/type/speed/pull bits are changed; PI7 encoder and PI9
LCD command data are preserved. The display's RGB bus configuration excludes
these status LED pins. The LED changes to green only after application
validation, copy and readback, immediately before the normal handoff.

Hardware facts come from the pinned
[TX15 hardware definition](https://github.com/EdgeTX/edgetx/blob/19b50d967e6e579ac5a1b3bdb014b148a6b47491/radio/src/boards/hw_defs/tx15.json)
and [GPIO LED driver](https://github.com/EdgeTX/edgetx/blob/19b50d967e6e579ac5a1b3bdb014b148a6b47491/radio/src/boards/generic_stm32/led_driver.cpp).
No EdgeTX application/runtime is used.

The display previously implemented each nominal millisecond as 128,000
iterations of a multi-instruction, stack-based volatile loop. The actual
instruction stream was examined; those iterations are not CPU cycles. r3
uses DWT cycle-counter elapsed time at the validated 128 MHz core profile,
unlocks the cold M7 counter if necessary, preserves CYCCNT, uses no interrupts
or SysTick, and bounds failures if the counter is absent or stops advancing.
All original panel reset/wake delays remain: 474 real milliseconds total.
Serial-command delays and panel commands are unchanged. This is the panel
wait budget, not a measured power-button-to-first-frame latency.

## Verification and candidate

The actual display initializer is tested with register/counter fixtures for
real elapsed waits, counter rollover, unavailable/stalled counters and
preservation of status LED modes. The new timing check failed against the
old loop and passed after correction. Nineteen focused tests passed, including
boot startup, QSPI, update routes, handoff and real ARM builds. Independent
review found no blocking issue; disassembly confirms no stack/RAM access in
the immediate LED path.

Candidate: `local/tx15-hardware/boot-instant-r3-20261023/`.
Raw/program bytes: 27,872 (already aligned to 32 bytes).
SHA256: `225f4c079eefc50dd6306cc77010655907ce5ccb5a03eecc96a0ecc86f6e1f6f`.
The internal-only installer defaults to r3 and accepts the exact installed
r2 full-bank hash. It preserves the current application, models and calibration.
Recovery of an older session requires its matching `--candidate` folder.

Installed on 2026-10-23: full internal-bank readback matched, external first
MiB remained byte-identical, and the CPU was confirmed halted at exit.
Evidence: `evidence/2026-10-23/boot-instant-r3-installed.json`. Current backup
and command journal: `local/hardware-session/boot-only-20261023-222957/`.
LED visibility, release-on-blue operation, screen timing and USB update entry
acceptance remain pending user observation.
