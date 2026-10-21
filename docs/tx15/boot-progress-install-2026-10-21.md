# TX15 power-on progress BL, internal-only installation

The existing application updater cannot write the internal bootloader. Use
PWLINK2 once to install the progress bootloader; preserve the current external
application, models and calibration. The user authorized this installation.

Candidate: `local/tx15-hardware/boot-progress-20261021/tx15-boot-usb.bin`.
Raw 27,592 bytes, SHA256
`bc4e7c93d36da80e5adcc06b27d0ba88cee523c88f6724d06bb51b76b08d9221`.
Programming pads to 27,616 bytes (32-byte alignment), SHA256
`450bc5c9940c9eec82e48f9e3995e743aaa48aefc0bfc0bb91acd458d92ff325`.
Only internal bank `[0x08000000,0x08020000)` is erased.

`utils/hardware/boot_only_update.py --install --arm` validates the candidate,
pinned RAM reader and target UID before writing. It captures the current
internal 128 KiB and external first 1 MiB, saves and reads back the backup
files, then binds a durable command journal to those bytes. The old installed
BL must match the reviewed historical image before an erase is permitted.
Every external erase/program intent is refused. The first external MiB is
compared before and after writing; internal verification covers all 128 KiB,
including erased padding. No external Flash write commands are issued.

All exits leave the CPU halted. Keep battery/probe connected until the tool
finishes. On success, disconnect probe and data USB, disconnect battery for
five seconds, reconnect and start normally. Confirm the POWER ON / RELEASE
POWER KEY, LOADING and STARTING feedback, application entry, then EXIT+power
USB UPDATE entry. Feedback begins after SDRAM/display initialization; this
does not promise instantaneous display at the first key press.

On interrupted internal programming, do not attempt normal boot. Restore with
the same tool and `--recover <boot-only-session-folder> --arm`; this validates
the saved plan and restores only the original internal bank, also verifying
that external application/settings match the snapshot. Snapshots and durable
results are kept in `local/hardware-session/boot-only-<timestamp>/`.

Offline validation: six internal-only transaction tests and 38 existing journal,
SWD, recovery, boot firmware and USB screen tests passed. Physical installation
has now completed: internal 128 KiB readback matched, external first 1 MiB was
unchanged, and the CPU was confirmed halted at exit. Evidence is in
`evidence/2026-10-21/boot-progress-installed.json`; the current backup and full
command journal are in `local/hardware-session/boot-only-20261021-215401/`.
User observation of cold-boot feedback and USB entry remains pending.

Recovery also requires the original candidate and `usb-boot-kit` folders;
preserve these with the session snapshot. Recovery does not load the saved
reader copies directly. Independent review found no blocking issue for this
installation with those inputs available.
