# TX15 UI03 card firmware implementation plan

> Execute inline using executing-plans and test-driven-development; one final
> independent review. No hardware access or automatic flash.

Goal: installable main-menu cards and dense Complex Mix editor, using the
approved 2026-10-27-tx15-card-ui-design.md (2026-10-28 density revision).

Constraints: preserve native Deviation, callbacks/model/settings ABI1, BL,
Map0, wheel UI02-R1, ELRS Lua, audio/storage. No emulator. Existing dedicated
dev/tx15-hardware-bringup checkout. Add opt-in TX15_CARD_UI requiring menu touch.

- [x] Test actual menu layout: two rows with three cards each; card hit gaps,
  real filtered enumeration, last page and selection. Keep UI02 tests valid.
- [x] Implement procedural icon cards, scoped dark palette, native menu row
  counts and hit mapping. No new bitmap resources or external framework.
- [x] Test dense Complex Mix geometry and hidden More fields. Reuse plate
  TextSelects, existing source/switch capture and value callbacks. Add generic
  value editing and bounded release-only touch routing only for adapted pages.
- [x] Implement Complex primary Src/Switch/Mux/Scale/Offset, live graph and
  curve selector; More exposes count/current mixer/trim. Header retains
  template selector; OK/Cancel preserve original callbacks. Simple/Expo keep
  legacy layout until separately adapted; never route touch to those boxes.
- [x] Test plate drawing without image-map dereference and physical/touch
  editing/exit; verify page teardown, child curve pages, no cross-page capture.
- [x] Run relevant full host checks, ARM build, independent review and fixes;
  package UI03 .ndu, record exact scope/limitations, commit/push dev branch.

Ledger: baseline b319556f. User approved main menu and denser Mix visual, asks
to try actual firmware. Trial UI03 may differ in font/rounded-corner details
because it uses current native font resources, not desktop PNG assets.

Completion ledger:
- Menu/card bounds and Mix geometry regressions were observed failing before
  their implementations. Native card enumeration, renderer/theme and value
  editing added; corner-clear regression caught stale outline clearing.
- Main implementation complete for three menu categories and Complex only.
  All controls/save data callbacks reused. Input/GUI routing keeps legacy
  templates/child pages out of touch. Numeric touch toggles edit; wheel adjusts.
- One independent reviewer found no confirmed blocking issue. Remaining live
  risks: linked-object rebuild, child return and actual save/cancel acceptance.
- Final 59 host checks passed; 157 ARM objects built/linked. Checked UI03
  marker/symbols/ND15 segment bounds/NDU CRC/ABI1; resources unchanged 464375B.
- USB package 718432B, SHA256
  ba980a7e311183f33d61cd34468dc6d9db0fecd4228f70e09efedcdbc7fb3efa.
  Evidence: docs/tx15/evidence/2026-10-28/card-ui03-candidate.json.
  No device access or Flash writes. All implementation tasks above completed;
  actual radio acceptance remains with the user.
