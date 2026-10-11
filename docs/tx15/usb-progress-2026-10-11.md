# TX15 USB updater evidence — 2026-10-11

The installed Deviation application is unchanged. No external/internal Flash
erase or programming was issued during either RAM test below. This is partial
bring-up evidence, not USB updater product acceptance.

## Current software (final offline candidate)

The complete final suite passed **244 tests / OK in 80.397 seconds**, with no
live hardware session. Integrated resident boot selection/error recovery,
NOR controller backend and USB servicing, update screen, Python client and
Windows GUI are implemented. Host failure injection covers wrong UID/session,
backup save/readback failures, interrupted COMMIT and no resending of COMMIT.
The normal boot path is exercised through actual Boot_Main with fake MMIO;
QSPI failures enter a read-only diagnostic updater, never a writable fallback.
Selecting an unreadable or oversized file clears any previously selected image.
Both fixes followed failing regressions and passed after implementation.

Legacy build tests now use temporary output directories. The original frozen
boot-chain ELF/BIN were reproduced from their exact original sources at the
original source paths and match unchanged production pins; their approvals
were not relaxed. Shared source bytes were restored before verification.

Resident boot raw BIN: 27240 bytes, SHA256
`ed12230e1db8acf6ccc46096106bc2da6cd81d58e4b3f17fb431b91a308a4465`.
ELF: `68ce60ed302d930465334ecee80abbe76262162c8187de6944f272b6dfae2f10`.
Build size: 27208 text / 32 data / 13000 BSS. The isolated build verifies
128KiB Flash, 56KiB RAM limits, vectors and matching ELF/BIN.

Windows onedir executable: `local/tx15-usb-release/NewDeviationUpdater/`;
EXE SHA256 `e6cefeefd2e332d5ed92b2b562fbf9be546651ebcb263f91a1458728f3c7628f`.
A new packaged process started successfully with PATH restricted to Windows,
without Python or a developer venv in PATH. Its smoke report records a visible
window, disabled update button and no automatic device opening or Flash writes.
This is GUI startup evidence, not physical USB update acceptance.

At the user's request, the next separate fresh-backup session is skipped.
The one-time kit reuses the validated pre-update snapshot in elrs-commands-kit
and freezes the actually installed calibration app unchanged. Recovery ZIP
extraction and the full kit reader passed. Installation must still compare all
live internal128KiB/external1MiB bytes; any changed settings abort before erase.
No hardware was opened or Flash written while preparing this kit. The resident
boot installation and full USB Flash update still require concrete approval
and physical acceptance; see [installation checklist](usb-boot-install-2026-10-11.md).

## Read-only physical sessions

Candidate BIN SHA256:
`5f1b46f1b6940644a1863dc542fab78d336e3a0aa5084a3c291dd20cc44ef152`.
The frozen read-only RAM initializer established power/clock and halted
in thread mode; the separate USB binary was uploaded and read back before run.
The probe binary contains no NOR writer. Both runs ended halted and closed.

| Evidence | First run | Second run |
| --- | --- | --- |
| Full local report | `local/hardware-session/usb-probe-20261011-100538.json` | `local/hardware-session/usb-probe-20261011-101028.json` |
| Advancing tick at end | 120072 ms | 120061 ms |
| Probe state / error | 3 / 0 | 3 / 0 |
| Requests / mounted / synchronized | 0 / 0 / 0 | 0 / 0 / 0 |
| GPIOH IDR | `0x1000` (PH5 low) | `0x1000` (PH5 low) |
| RCC CR / USB clock select | `0x0303F025` / `0x00300000` | same |
| PWR CR3 / OTG DCTL | `0x05000042` / `0x2` (soft disconnect) | same |
| Host CDC acceptance | No reviewed identity enumerated | No reviewed identity enumerated |
| Flash mutation commands | 0 | 0 |

After the first run, the user confirmed normal Deviation recovery and clarified
that the target USB cable had not actually been inserted. It cannot diagnose
a driver failure. Before the second run the user explicitly confirmed the target
data cable was inserted and separately reconnected PWLINK2. Despite that, PH5
remained low and the firmware stayed soft-disconnected. The next check is the
actual target connector/cable; port, cable, board mapping and detector behavior
are not yet distinguished. No bypass of VBUS or firmware fix is justified yet.

The PC checker never opened a target serial device or sent BEGIN/DATA/COMMIT.
After the second run, the user reported the cable itself had a problem and was
now fixed. No firmware change was made to bypass insertion detection.

## Replacement-cable result and receiver fix

Windows enumerated `VID_CAFE/PID_4015` with the reviewed UID as COM36. The host
received and verified HELLO, including the read-only flag. The mailbox recorded
mounted=1, synchronized=1, PH5 high (`GPIOH IDR=0x1020`), DCTL=0. This proves
enumeration, the device identity, clock synchronization and a protocol exchange.
It does not prove complete firmware reception.

BEGIN then faulted: probe state=8, CFSR=`0x400`, HFSR=`0x40000000`, one prior
request handled. Saved read-only fault evidence:
`local/hardware-session/usb-probe-fault-20261011.json`. Inspection showed that
the frozen `boot/bench.c` initializer does not initialize SDRAM; the USB probe
incorrectly assumed it did. Its first staging write therefore targeted an
uninitialized external RAM controller.

The probe now calls the existing native SDRAM initializer before USB startup.
An actual ARM build regression test failed on the missing SDRAM initializer,
then passed after the fix; it checks the call precedes USB initialization and
still excludes NOR mutation code. The separate fixed candidate is in
`local/tx15-hardware/usb-probe-sdram`, BIN SHA256
`8fc57928db7d3230589c5102ca0eb3ccf0b90b8ffd2f27523d00a984227f6f2a`.
The fixed build has 17152 text / 24 data / 11800 BSS bytes and has not yet
passed physical full-package reception at the time of that build.

The PC checker also has a bounded retry for the initial Windows COM-path
creation delay, before any protocol traffic. Tests refuse writable/unknown
HELLO flags and a mismatched UID before BEGIN. Opening a port is retried;
mutating protocol operations are not automatically replayed.

One complete-suite run overlapped the live PWLINK2 lease and consequently
failed four installation-fixture assertions with a lock conflict. The lock was
not bypassed. A rerun without an active hardware session passed: 220 tests / OK.

## Remaining acceptance

Unplug/replug, resident normal boot/EXIT/error entry, actual NOR writing,
concrete approval for the first resident installation, a complete physical USB
Flash update, and preserved model/calibration checks remain pending. The GUI
and resident/backend software builds are complete; hardware acceptance is separate.

## Fixed-probe physical acceptance

The fixed candidate subsequently passed actual USB transfer of the complete
694896-byte `.ndu` package (694768-byte ND15 image). Device validation reached
READY, and the negative COMMIT test returned READ_ONLY without a Flash write.
The final mailbox recorded state3/error0, 683 requests, received694768,
mounted1/synchronized1 and SDRAM state2 at tick90123. The session number matched
the host report. Candidate upload/readback and the final CPU halt were verified.
The user then power-cycled and confirmed normal Deviation recovery.

Curated evidence: [usb-readonly-ram.json](evidence/2026-10-11/usb-readonly-ram.json).
This proves the USB identity, complete RAM reception/validation and the read-only
guard. It does not prove resident boot selection, USB unplug/replug, NOR hardware
writing, Windows GUI delivery or a full application Flash update.

While advancing transaction integration, a regression test also exposed STATUS
reporting ERROR during the pre-write shadow backup. Preparation now reports
VALIDATING with no error while servicing the host, until an actual failure or
the erase phase. This changed only the tested transaction core; the RAM probe
does not link that core. The runtime regression failed first, then passed, and
the transaction failure-injection test passed.

## One-time resident boot installation

User explicitly approved the concrete kit. Initial probe opens failed before
reset/write; direct PC USB connection restored PWLINK2 enumeration. The armed
held-power/release procedure then established power hold. Complete live internal
128KiB/external1MiB bytes matched the reused snapshot before the first erase.
The same installed app was programmed, full external readback and untouched
tail/model/calibration checks passed, then the new internal boot was programmed
and the entire 128KiB bank verified. Journal state=installed, sequence3647,
checkpoints external/internal; final halt verified. No new snapshot was saved.
Curated evidence: [usb-installed-swd.json](evidence/2026-10-11/usb-installed-swd.json).
Normal cold boot, EXIT USB entry and full USB Flash update remain pending.
