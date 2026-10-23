# TX15 PW01 shutdown countdown

The user accepted the r3 immediate power-on feedback and requested a visible
shutdown countdown. PW01 is an application-only USB update. The installed r3
bootloader and the model/calibration ABI are unchanged.

After the existing 20 ms initial release guard, holding POWER opens a central
panel with a large 2/1 countdown, an amber progress bar and RELEASE TO CANCEL.
The existing continuous two-second hold threshold is retained. Releasing the
key restores exactly the saved pixels and resumes the same GUI or Lua caller;
a later hold starts from zero. Completing the hold displays SAVING / PLEASE
WAIT, then calls the existing model/calibration save and power-cut path.

The modal does not dispatch GUI callbacks while active. It repeatedly services
the native runtime: controls/analog sampling, mixer and RF model updates,
Lua transport, battery, storage and audio services continue. SysTick and RF
UART interrupts remain enabled. Rendering yields between large rectangle rows
and only increments the progress fill between digit changes. A busy guard
protects watchdog reentry. No settings writes occur on cancellation.

Only the 360x192 panel at (60,64) is captured. Its 138,240-byte snapshot uses
`0xd0200000..0xd0221c00`, after normal application resources and the optional
display shadow. It reuses the expired USB-updater shadow / RAM-chain source
only after application handoff. The modal writes the visible framebuffer
directly and leaves GUI font/object state and Lua state untouched.

The actual new module harness covers boot-press exclusion, cancellation,
byte-exact restoration, repeated holds, clock rollover, service continuation,
watchdog reentry and drawing bounds. Thirteen relevant tests passed, 150 ARM
objects built and linked, and independent review found no blocking issue.
The application contains the shutdown UI and does not enable the previously
withdrawn buffered-display path.

USB file: `local/tx15-usb-release/tx15-power-countdown-20261023.ndu`.
About identifies `New Deviation TX15 PW01`. Package 709,744 bytes; SHA256
`57334f5584dd0793a9345aa5c4a04bd2a9c108e231992b1a1e8191523bca879e`.
Boot API 1 and settings ABI 1. Complete package/header/image CRC and ND15
segment/vector validation passed. See
`evidence/2026-10-23/power-countdown-candidate.json`.

Install through the existing USB UPDATE entry (EXIT+power) and dedicated
updater, then power-cycle. Physical acceptance is pending: check appearance,
release-to-cancel on a normal page and ELRS Lua page, hold-to-shutdown, and
normal restart with the existing model/calibration. Cancellation should also
preserve an established ELRS link; host service tests are not RF acceptance.
