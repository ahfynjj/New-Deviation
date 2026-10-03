# Native TX15 RAM application (P2)

Build with `python utils/build-tx15-app.py` from the repository root using the
existing Windows toolchain. The output `local/tx15-hardware/app/tx15-app.elf`
is a finally linked ARM executable, with its load map automatically checked.
Hardware acceptance remains a separate step. No Flash installer is provided.

The proven RAM bootstrap initializes power, clocks, SDRAM and the display.
A second stage loads application code at 0x24010000 and read-only resources at
0xD0080000, checks each block by readback, then enters the application in Thread
mode. The 16 KiB stack ends at 0x24080000. Bootstrap, mailbox and framebuffer
are excluded from application load ranges. Existing recovery restores the
original firmware after the temporary session, including failure paths.

Original Deviation main/mixer pages, GUI and model/mixer code are compiled.
Encoder/key events feed Deviation buttons. Fonts and icons use original file
decoders through a read-only resource adapter; SDRAM reads explicitly use bytes
because this stage leaves the MPU disabled. Model edits are RAM-only.

This is a bench application: the ordinary build keeps RF disabled; six ADC1
inputs, calibration and a specific conditional mixer model have passed prior
board checks. Battery voltage is unmeasured; audio/USB/storage are unavailable.
It must not be used for flight. See TODO.md and bench records for current
ADC, mixer and ELRS acceptance; storage/USB/standalone boot remain pending.

The opt-in RC bench uses `TX15_ELRS_LUA=1 TX15_ELRS_RC=1` (and optionally
`TX15_ELRS_WRITE=1`). It embeds a separate AETR model with Module=Off by
default. Model setup -> CRSF options -> Module=Internal activates the proven
internal UART. Off and Ext pending stop RF; external hardware is not enabled.
Seven main-page bars show AETR, fixed-low CH5, S1 and S2. Wire CH5 and CH14
are forced low even if the bench model is edited; this is not universal
receiver/flight-controller arming protection. Long PAGE opens official Lua;
long EXIT returns to the main page and keeps RC. A 180-second whole-app bench
limit stops RF; the debug host must still restore original firmware.

SysTick submits the last complete RC snapshot every 4ms, independently of
Lua. Main-task cooperative services sample/mix/publish; 100ms-old samples
stop RC submission. This is a handset UART schedule, not the configured
over-the-air packet rate or receiver failsafe proof. RC and tool frames are
copied under short interrupt masks; the router is never called in IRQ.
The tool queue is flushed on script close/error without stopping RC.
Telemetry interpretation and cold-start storage/independent boot are pending.
