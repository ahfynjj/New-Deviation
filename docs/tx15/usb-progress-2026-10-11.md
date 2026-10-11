# TX15 USB updater evidence — 2026-10-11

The installed Deviation application is unchanged. No external/internal Flash
erase or programming was issued during either RAM test below. This is partial
bring-up evidence, not USB updater product acceptance.

## Current software

Committed package validation, bounded framing/RAM receiver, isolated TinyUSB
CDC probe, transaction core and runtime gates: `6268408c`, `067d0370`,
`527e9fde`, `9be8bdd9`. The current complete suite finished with 218 tests / OK
(66.584 seconds); the USB-focused suite finished with 16 tests / OK before
additional geometry mutation cases were included in the complete run.
Native bounded NOR geometry assessment has now been added and compared with
the existing Python SFDP/protection policy; hardware NOR commands and resident
USB boot integration remain pending.

## Read-only physical sessions

Candidate BIN SHA256:
`5f1b46f1b6940644a1863dc542fab78d336e3a0aa5084a3c291dd20cc44ef152`.
The frozen read-only RAM initializer established power/clock/SDRAM and halted
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
now fixed. Replacement-cable USB acceptance is pending. No firmware change was
made to bypass insertion detection.

## Remaining acceptance

USB enumeration, real RAM package transfer/READY/read-only COMMIT rejection,
unplug/replug, observed clock synchronization, integrated NOR backend/resident
boot, Windows GUI and packaged delivery, fresh device baseline and explicit
approval for first resident installation, then complete physical update and
preserved model/calibration checks are still required.
