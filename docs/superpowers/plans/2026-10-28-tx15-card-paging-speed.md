# UI03-R1: discoverable seventh menu item and bulk raster fills

Baseline 9f579e53. User accepts UI03 appearance, reports missing Storage test
and general lag. Storage is the seventh enumerated item while each viewport
shows six. Reproduce/verify real linked menu navigation, not only mocked rows.

- Test real GUI scrolling/selection reaches all seven items and Storage via
  Next and rotary. Add explicit total/page information to Next footer; avoid
  silently presenting a six-item menu. Do not remove or relocate tools.
- Reproduce slow paths using actual lcd_gfx.c and counters: FillRect/H/V
  currently route every pixel through LCD_DrawPixel; rounded cards fill two
  large rectangles per tile. For native frame swap only, use the existing
  bounded tx15_frame_rect writer; retain service calls and frame ownership.
- Test colors, clipping, zero size, rounded shapes, dirty-frame semantics and
  no primitive-level present. Other targets retain old raster path.
- Run relevant host suite, ARM build and one independent review; package
  UI03-R1 with ABI1 and current BL/model/calibration unchanged. User verifies
  speed on hardware; host operation counts are not measured device latency.

Use systematic-debugging + executing-plans inline. No hardware access or
automatic flash. Existing dedicated dev branch checkout reused.

Completed ledger:
- Actual linked-row scrollable test reached all seven before its final missing
  page-caption assertion failed. Added page caption; complete regression passes.
- Actual raster test failed on old per-pixel path. Bulk fill/line path now
  passes colors/clipping/zero/rounded checks, retaining the existing service.
- Final 61 related tests passed; 157 ARM objects linked; marker, NDU/ND15 CRC,
  bounds and ABI1 verified. One independent review found no actionable issue.
- Hardware speed remains pending; neither host checks nor review are a
  measured frame-time result. No device access or Flash writes.
