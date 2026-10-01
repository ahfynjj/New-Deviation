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

This is a bench application: RF is disabled; the P3 build now includes ADC1 polling (not yet board-verified),
battery voltage is unmeasured, and audio/USB/storage writes are unavailable.
It must not be used for model control. Real ADC/ELRS/storage are later milestones.
