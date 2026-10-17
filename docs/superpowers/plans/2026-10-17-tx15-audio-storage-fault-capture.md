# TX15 audio/storage fault capture plan

> Execute inline with executing-plans. Scope is failure observability, not a speculative hardware fix.

User STO0 report: audio Tests0/DMA25/Errors9/Underruns0; storage Error0/HW0,
0MiB/SDSC/RCA0/CMD0/STA00002000/RESP0/Reads0. Earlier storage report was Error2.
Neither audio nor storage hardware acceptance passed. These observations do not prove that
the medium is absent or that the audio codec works. STA bit13 is CPSMACT; the timing of
the second report relative to Scan/deadline/Stop is unknown.

- [x] Add failing tests for exact audio failure reason, failing register, retained I2C/DMA status,
  and storage pre-cleanup clock snapshot; show state/elapsed time/poll gap on the pages.
- [x] Add bounded snapshot reads only. Preserve errors through cleanup/page re-entry and reset
  per-attempt diagnostics only when a new attempt starts. No changed clock/protocol/timeouts,
  no extra initialization or storage write commands; keep model/calibration/bootloader contract.
- [x] Run targeted and focused regression, ARM build, NDU integrity/ABI/range checks and review.
- [ ] Record raw user feedback and proof limits, commit/push, provide one combined USB package.
  One Play and one Scan after restart should expose the failure stage; obtain page photos.

Verification:46 tests29.992s;148 ARM objects; pre-cleanup CMD17 snapshot-loss finding
fixed via failing regression. NDU and memory evidence recorded in
docs/tx15/evidence/2026-10-17/audio-storage-fault-capture.json. Device not accessed.
