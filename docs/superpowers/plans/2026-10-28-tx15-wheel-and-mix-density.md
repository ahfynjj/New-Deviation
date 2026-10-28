# TX15 wheel detents and Mix density

User: keep the proposed main menu; Mix needs more information; wheel should
move one item per detent. Work in existing dev/tx15-hardware-bringup checkout.

1. Reproduce slow detents in the pure decoder and fast turns through actual
   ScanButtons/BUTTON_Handler. Check bounce, reverse, invalid Gray transitions,
   physical ENTER/EXIT, and no long-press from synthetic wheel events.
2. Use two valid Gray edges per TX15 detent, preserving direction and partial
   cancellation. Native physical inputs already debounce 20ms. Reduce native
   second debounce to 10ms and wheel pulses to 20ms on/20ms off; leave other
   transmitter targets unchanged. Preserve up to 32 queued detents.
3. Revise Mix design only: five 40px parameter rows plus compact curve preview,
   visible switch/mux/source/scale/offset and explicit remaining fields. Keep
   40px footer and all existing Deviation fields/save semantics. Main menu
   preview unchanged. Native card implementation is a later firmware stage.
4. Run focused/full relevant host checks, ARM build, one independent review;
   package USB UI02-R1 app, preserve BL/settings ABI, record evidence and push.

Evidence: hardware/tx15/board/input_filter.c currently requires four edges;
docs/tx15/bench-2026-10-01.md records two detents per menu item. platform.c
currently synthesizes 100ms press+100ms release; src/buttons.c debounces 80ms.
These are code/previous hardware observations, not a fresh device capture.

Live acceptance pending USB update: ten slow detents each way -> ten items;
moderate speed, immediate reversal, edits, ENTER/EXIT and ELRS Lua navigation.
No device access/flash in this development session.

Execution ledger:
- Initial two-edge detent regression failed; real fast-turn BUTTON_Handler
  regression also failed before changing production code. Both now pass.
- Mix mock revised and visually inspected; 18 nonoverlapping 40px-minimum hit
  targets checked across both screens. Main-menu mock unchanged.
- Independent review found no blocking bug, noted missing physical-key and
  longpress host coverage. Added ENTER long-hold/EXIT short-hold and wheel
  no-longpress checks through the actual callback dispatcher; passed.
- Final 51 relevant host tests and 156-object ARM build passed. UI02-R1 marker,
  ND15/NDU CRCs, ABI1, and settings boundary verified. Hardware acceptance pending.
