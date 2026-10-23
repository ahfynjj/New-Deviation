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
The first version failed cold-boot acceptance as described below.

## Cold-boot failure and r2 correction

The user reported that pressing only POWER entered USB UPDATE, displaying
WAITING / CONNECT DATA USB / READ ONLY. This first progress BL therefore failed
normal cold-boot acceptance despite correct Flash readback. The saved external
application passed header, segment CRC and vector validation on the host.

Root cause: early display initialization enables PLL3; the boot NOR initializer
still required RCC_CR to contain only the PLL1 clock state. The real QSPI host
harness reproduced rejection with PLL3 ON+READY. The guard now permits PLL3
fully off or ON+READY while retaining all PLL1, PLL2 and NOR clock checks.
Tests also reject incomplete PLL3 startup and missing PLL1 readiness. After
the fix the same harness passes. USB session initialization resets the
receiver's displayed ERROR to WAITING, explaining the observed status while
the updater remains read-only. No updater-status change is included here.

Replacement candidate: `local/tx15-hardware/boot-progress-r2-20261021/`.
Raw 27,624 bytes, SHA256
`f54425735f8f8c525c38e40a1852934abdfa0f4b97438aac00e389179772f149`.
Padded 27,648 bytes, SHA256
`53309bb9a1947ee4e57ca6153ab7de3619eb3430f3cb1d36d4e9bf3da1397741`.
The BL-only tool defaults to r2 and accepts the exact installed r1 full-bank
hash in addition to the original USB BL; unknown banks still stop before erase.
Fourteen relevant tests passed and the resident USB ARM build completed.
r2 was installed on 2026-10-23. Full internal-bank readback matched and the
external first MiB remained byte-identical, including models and calibration.
The CPU was confirmed halted at tool exit. See
`evidence/2026-10-23/boot-progress-r2-installed.json`; current backups and
the journal are in `local/hardware-session/boot-only-20261023-220708/`.
The user confirmed r2 shows POWER ON/LOADING and enters Deviation, but feedback
still appears too late. The immediate acknowledgement correction and its
acceptance boundary are described in `boot-instant-feedback-2026-10-23.md`.
USB entry acceptance after these changes remains a separate check.

Recovery also requires the original candidate and `usb-boot-kit` folders;
preserve these with the session snapshot. Recovery does not load the saved
reader copies directly. Independent review found no blocking issue for this
installation with those inputs available.
When recovering an r1 session, specify its preserved r1 folder explicitly with
`--candidate local/tx15-hardware/boot-progress-20261021`; the default is now r2.
