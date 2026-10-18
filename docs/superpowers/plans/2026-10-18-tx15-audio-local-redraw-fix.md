# TX15 quiet tone and visible redraw correction

Execute inline as fixes to the approved native GUI/audio work. User confirms max5
still very quiet and visible flashing mainly where content changes. Do not equate
this with the historical whole-screen/backlight flicker, which was absent after
first standalone installation. No current electrical/panel fault is established.

Code evidence: current label/bar repaint erases the background directly in the
LTDC scanout before writing new content. LCD_ForceUpdate is a no-op. Lua fill also
writes that same scanout directly. Audio max5 still writes40 to speaker attenuation
register46 (~20dB loss), in addition to the synthesized tone's amplitude reduction.

- [x] RED tests for invisible intermediate redraws, clipped dirty-region flush,
  no-op refresh, bounded hardware service during painting/copy and no memory overlap.
  RED checks for new attenuation table, mute and preserved low-gain codec settings.
- [x] Render to a shadow framebuffer atD0100000 after loader handoff; this reuses
  expired boot staging, does not modify loader/ELF memory acceptance. Copy only the
  completed dirty bounding rectangle to existing scanout at LCD_ForceUpdate;
  service runtime every512 pixel operations. This is compositing, not VSYNC or a
  claim of zero tearing. No LTDC/PLL/backlight/DMA2D changes. Route Lua fills/presents too.
- [x] Keep0..5/mute, gain+6dB/DAC-6dB/tone peak unchanged. Attenuation register
  values127(mute),72,48,24,12,0; default3. Max removes20dB old loss, default removes
  about16dB. No persisted volume/model-format change in this fix.
- [x] Regression/review/ARM/NDU guards:56 tests30.724s,150 ARM objects; no review blockers.
- [ ] User hardware test covers menu/channel redraw and increasing volume.
  Software artifact/evidence:docs/tx15/evidence/2026-10-18/audio-display-fix.json.
