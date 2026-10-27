# TX15 UI02: native menu layout and bounded touch

Spec: ../specs/2026-10-25-tx15-ui-touch-design.md

User verified approximate full-screen alignment and confirmed Map 0 on 2026-10-27.
Keep Deviation navigation, models, mixer, rotary controls, RF and installed BL.

1. Add regression tests for menu hit geometry, release-only taps, bounded swipes,
   cancellation, page/scroll changes, diagnostic ownership, and Map 0 override.
2. Add opt-in TX15_MENU_TOUCH requiring the existing native touch build. Enlarge
   MAIN MENU / Model menu / Transmitter menu to six 40px rows and 40px footer.
   Use existing 23bold font; Back / Previous / Next and vertical page swipe.
3. Route touch only from the GUI loop. Suspend at page transitions, Lua entry and
   shutdown modal. Never dispatch to legacy parameter pages; HAS_TOUCH stays 0.
   Keep Touch test's manual ownership and trial mapping independent.
4. Run relevant native host tests, ARM build and one independent review. Package
   UI02 .ndu preserving boot API/settings ABI 1, record evidence, commit/push.

Hardware acceptance: user USB update; check three menu pages, tap once per
release, swipe, footer, rotary, Touch test, Lua return, shutdown cancellation.
Mix/model parameter layout and Lua touch are later phases, not claimed here.

Execution ledger:
- Baseline faffe31c; existing dedicated dev checkout is clean.
- Map 0 is a user-observed direction, not proof of precision at every edge.
- Independent review: added observed-release gating after sampler restart. A
  100ms timer alone cannot reject a held finger after delayed discovery. Native
  driver regression reproduced the missing API/guard before implementation.
- Ruling: if GT911 has no initial zero-contact report, the first touch/release
  only arms menu input. Prefer one ignored entry touch over an accidental tap
  after Lua return or shutdown cancellation. Parameters remain rotary-only.
- Task 1-3 complete: three host regressions cover actual native menu layout and
  routing, hit geometry, gestures and ownership. Driver test covers held finger
  across 300ms bus contention plus fresh touch after release; modal guard tested.
- Task 4 complete: final 49 relevant tests passed; 156 ARM objects linked, UI02
  symbols/ND15/NDU/CRC and ABI validated; 715128-byte package. No device access.
  Evidence: docs/tx15/evidence/2026-10-27/menu-touch-ui02-candidate.json.
