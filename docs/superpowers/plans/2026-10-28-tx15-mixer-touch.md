# UI04 Mixer touch implementation

Baseline 23c137af. Continue approved native Deviation touch/card design.
No model/boot ABI changes, no simulator, no hardware access. Keep wheel and
UI03-R1 bulk rendering. Existing dedicated dev branch used.

Scope: native Mixer list, Simple and Complex fields. Expo and child curve/
limits/reorder pages remain rotary-only. Add release-only 40px +/- zones in
armed TextSelects; middle confirms. Reuse existing ValueCB and bounds, never
synthesize duplicate ENTER or wheel events. No automatic repeat while held.

1. Red tests: field step requires active selected editor, applies once,
   disarms on focus loss; hit IDs distinguish +/-/center and page generations.
2. Add editor step API, draw bounded +/- and value in the existing plate.
   Native Simple editor uses original gui1 objects/callbacks; Complex stays
   unchanged except touch adjustment. Capture Src/Switch still works.
3. Adapt actual Mixer list to five 44px rows and large channel/edit areas,
   Back/Previous/Next, Monitor/Order header. Use current list channel mapping,
   limits/virtual names and original templateselect_cb. No hidden overrides.
4. Route Mixer list gestures separately from Mix editor. Cancel at page/row/
   generation changes, and never route gestures to legacy child pages.
5. Run relevant full host suite, ARM build and one independent review; package
   UI04 USB app, preserve model/calibration/BL. Record software vs radio proof.

Design ruling: direct inline +/- rather than a new modal numeric keypad, to
retain callback bounds/capture/Cancel semantics and avoid extra page state.

## Completion evidence

All five steps implemented. 64 host tests passed; 157 ARM objects linked and
boot payload validated. One independent static review found no important
actionable issues. UI04 .ndu round-trip/CRC/ABI verified; package 719720 bytes,
SHA256 9712c31433d6be59959d1157c8e1224f19981ec2d3e30bd3758eb8d81b6940d9.
No device accessed or flashed. Hardware tap/swipe, save/cancel, capture and
navigation acceptance remains pending; release note lists the exact scope.
