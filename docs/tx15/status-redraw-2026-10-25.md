# RD01: Audio diagnostic redraw candidate

Audio test previously invalidated its entire 440x145 status label every 200 ms,
even when the report was unchanged. The label helper erased the background and
then drew glyphs directly into the visible framebuffer. This explains repeated
erase/repaint exposure in the region reported by the user; hardware acceptance
is still required to establish the visible improvement.

The report is now six cached 440x23 rows. Only rows whose formatted text changes
are invalidated. AUD4 in the page title and RD01 in About identify this build.
No audio driver, storage driver, RF configuration or settings schema is changed.

With TX15_STATUS_REGIONS enabled, short labels are composed in a bounded
480x32 RGB565 scratch area at 0xd0300000 (30,720 bytes). The visible region is
captured first, then background/border/text rendering is redirected to scratch.
After rendering, only the completed rectangle is copied back with aligned word
copies. The scratch area is separate from framebuffer, resources, the disabled
AV03 shadow and the shutdown modal's saved rectangle. Large labels remain on
the direct path. Labels whose text, alignment, selection inset or font height
would overflow their original box also remain direct, preserving legacy menu
rendering. The optimization is disabled by default and cannot be combined with
TX15_BUFFERED_DISPLAY in the application builder.

There is no pixel comparison, global dirty-bound scan, full-frame copy,
vertical-sync wait or interrupt masking. This is not an atomic display swap:
copying into active scanout can still tear. DWT counters retain maximum drawing
and commit cycles, but no target timing has been collected for this candidate.
Other direct drawing paths, including full-page Lua rendering and bar graphs,
are outside this change and may require separate work after physical feedback.

## Verification

16 focused tests passed, including actual label/LCD adapter composition,
edge clipping, odd X alignment, nested-region rejection, and direct-versus-
composed frame comparison for overwide/overheight/selected labels. The overflow
regression failed before the footprint guard and passed afterward. Audio tests
check zero idle invalidations and only changed status rows. Existing power UI,
USB package, RF model, official Lua runtime, settings, media clock and audio
checks passed. The ARM build compiled 151 objects and validated the load map and
ND15 payload. Independent review found no remaining blocking issue.

Reproduce the host checks:

```powershell
$env:PYTHONPATH='utils;utils/hardware;utils/hardware/tests;.'
& '..\tools\pyocd-venv\Scripts\python.exe' -m unittest test_display_region test_audio_page test_app_adapter test_power_ui test_usb_update_package test_audio_hw test_media_clock test_lua_runtime test_rf_model test_settings_store
```

For utils/build-tx15-app.py, set TX15_STANDALONE, TX15_ELRS_PRODUCT,
TX15_ELRS_RC, TX15_ELRS_LUA, TX15_ELRS_WRITE, TX15_PERSISTENCE, TX15_AUDIO,
TX15_STORAGE and TX15_STATUS_REGIONS to 1, and TX15_BUFFERED_DISPLAY to 0.

USB package: local/tx15-usb-release/tx15-status-redraw-20261025.ndu
(710,768 bytes), SHA256
`2c11b8673f1b6e7724fe9e9a9f194397cc19445ed8373af61042dedb8e2c717f`.
Header and image CRC, ND15 segment/vector validation, Boot API 1 and settings
ABI 1 passed. The ELF contains the region compositor and power countdown and
does not link the old display-buffer implementation. See
evidence/2026-10-25/status-redraw-candidate.json for build/package hashes.

## Physical acceptance pending

Use EXIT+power to enter USB UPDATE and install the NDU with the existing
dedicated updater. This updates the application, retaining the installed
immediate-feedback bootloader and settings area. Restart and confirm AUD4.
Observe the untouched Audio page for 15 seconds, then play once and change
volume. Check the upper rows for flicker, ordinary menu responsiveness, and
model/calibration retention. Confirm ELRS link continuity separately.
No device was accessed or Flash written during preparation of this candidate.
