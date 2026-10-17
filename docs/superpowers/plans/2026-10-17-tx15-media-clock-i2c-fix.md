# TX15 media clock and bounded I2C correction

Execute inline. Evidence: IMG_4992 AUD1 Reason6/Step4/Reg10/I2C00008001,
Init281ms/Gap16ms/Tests0/DMA3/Errors1/U0; IMG_4993 STO1 Error2/CMD0/
STA2000/Time282ms/Gap142ms/CLK A0/PWR3/PLL01090898/SEL0/CMDR1000/Reads0.

ST v1.11.2 LL_RCC_PLL1Q_Enable requires PLL1 disabled. PLL1Q bit17 in the photo
is0 despite the request: old S0 mock wrongly allowed a live write. Do not stop
CPU PLL1 or replace the bootloader. Prepare fixed PLL2 P/R media clock once at
application start; enable both outputs before PLL2 starts. Keep it through page
exit, so audio stop cannot remove the storage clock. P unchanged49.15198MHz;
R196.60791MHz and SD divider246 gives399.61kHz. Preserve PLL1/3/NOR guards.

Audio busy/TXE snapshot has no NACK/BERR; 1ms tick subtraction can expire a
sub-ms transaction at a tick boundary. Test that defect with independent cycle
timing, use DWT CYCCNT for actual1ms audio deadline, no retries/bus reset, retain
input timing and audio setup. This is a demonstrated software defect and a
candidate explanation of the photo, not yet the accepted hardware root cause.

- [x] RED tests: PLL output write protection; fixed clock survive audio/storage
  stops, invalid clock rejection; I2C tick-boundary false timeout and true1ms hang.
- [x] Minimal clock owner, native runtime/build wiring, transport changes and
  bounded cycle timer. Preserve readonly commands and all diagnostic fields.
- [x] Focused review/regression, ARM/NDU guards, updated evidence and one USB
  candidate. No device access, medium write, model migration or bootloader change.
- [ ] User: one Scan and one Play; hardware acceptance separately.

Final software evidence:49 tests30.142s,149 ARM objects; guarded DWT LSR/LAR
unlock added after review with observed failing/passing regression. Package and
photo hashes in docs/tx15/evidence/2026-10-17/media-clock-i2c-fix.json.
