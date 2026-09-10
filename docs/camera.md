# Experimental camera options

SETTINGS provides two independent battle controls:

- **Battle view:** 4:3 or 16:9. Native widescreen extends the horizontal rendering
  surface instead of stretching characters.
- **Battle zoom:** 100%, 90%, or 80% projected size. At 80%, the same viewport
  covers approximately 25% more world span along each axis. This changes the
  effective field of view; it does not move the scripted camera backwards.

They can be combined. Defaults retain 4:3 and 100%. Changes persist in the
existing mod state and apply to ordinary battles (mode `0x600`). Fields, the lab,
card battles, full-screen menus and rewards retain their original view. In 16:9,
enemy health, battle commands/submenus and bottom dialogue stay aligned on the
left; player health/MP and the miniature portrait move to the right. HUD sizes
remain unchanged. The 4:3 layout retains the original positions.

These are experiments, not a claim that every arena or cinematic was authored
for the expanded framing. Attack effects, arena boundaries, sky geometry and
game-side culling need coverage across more battles.

## Implementation

`src/view.c` separates persisted preferences from the effective scene settings.
`src/view_frontend.inc` configures the pinned runtime's native-wide compositor,
updates presentation aspect, and gates gameplay presentation on the battle mode.
`tools/view.cmake` generates a local copy of `gte.cpp`. Its projection hook scales
the X/Y perspective terms before adding OFX/OFY. H, camera transforms, SZ, lighting
and depth cue calculation retain their original values. Ordinary HUD sprites do
not pass through this hook. The framework checkout is never edited.

`src/battle_hud.c` translates collected host GPU commands in the battle's
zero-origin HUD draw environment, leaving guest packet RAM and arena geometry
alone. Submenu panels move together, including Tag bars and DV choices that
cross the old midpoint. The portrait's separate viewport, origin and backdrop
move together to the right. Generated GPU/GL copies retain its horizontal clip
and wide target in both vertical framebuffer bands. The animated cursor uses
twelve 12x12 CopyImage tiles at VRAM y=244; `src/battle_hud_gpu.inc` draws those
through the renderer facade so a negative left-margin destination cannot wrap
into texture memory. These hooks are gated on ordinary battle mode and an
active native-wide view.

Debug tooling uses `shinka_nav` operation `view`. With no arguments it reports
stored width/zoom and effective wide/percent values. To persist a choice, supply
`option: 0` (width, values 0..1) or `option: 1` (zoom, values 0..2), plus `value`.
Use `screenshot` or `wide_shot` for native-wide captures; `screenshot_file` only
captures the original 320-pixel VRAM rectangle and omits the extra sides.

## Verification

The Windows Release build passed nine native suites and all 70 Python tests.
Native camera checks cover the six combinations, scene isolation and a scene
change between frontend ticks. Menu checks cover both roots, persistence failure
and BACK migration from the old four/five-row settings layouts.

Live OpenGL checks used copied cards and a Central Park Kunemon battle checkpoint:
all six combinations survived state reload, captured at 320x240 or 426x240 as
appropriate. At 16:9/80%, the attack, victory and field return completed; Central
Park and Status rendered at their original 4:3 with effective zoom reset to 100%.
Both quick-menu and full-screen SETTINGS controls changed persisted values via
ordinary directional input, and cancel returned the highlight to SETTINGS.
Local captures are under `output/view-01/`; these tests do not establish coverage
of every arena, special attack or story cinematic. Headless mode can exercise the
projection logic but did not supply a composed wide surface in this setup.

The HUD follow-up passed all nine project native suites (excluding the upstream
unbuilt `example` target). Added checks cover panel translation, UV/size
preservation, wide Tag bars, description text, portrait clipping in both bands,
all twelve cursor tiles and rejection outside the supported environment.
Live copied-save checks under `output/hud-01/` cover Fight, Tech, DV, Tag and Item
layouts, all six width/zoom combinations on the Tech screen, and left-aligned
attack dialogue. Player settings were restored after the diagnostic run.

## Field expansion audit

The field is a layered tile renderer, not the battle's 3D projection. Independent
inspection of the supported FIELDSTG instructions found:

- File offset `0x364c`, loaded at `0x800862fc`, starts a streaming/draw routine
  with a `0x160`-byte stack frame. Its temporary tile list starts at SP+0x18;
  saved registers begin at SP+0x138. Twelve 24-byte entries fill that space.
- `0x37c8` / `0x37d8` bound its enumeration to four columns and three rows of
  128-pixel cells. The starting cell is derived from camera origin minus small
  look-ahead margins, clamped at the map's top/left edge.
- `0x39e4` selects among twelve texture-resident slots; per-slot state occupies
  three words beginning at owner+0x74. Raising just the enumeration limits would
  overwrite the stack and would not supply additional resident textures.
- The camera updater at file offset `0xaad8` follows position minus (160,140)
  and clamps against map size minus (320,240). Transition effects elsewhere
  also use 320/240 constants, so a global immediate replacement is inappropriate.

Field work must account for the temporary list, texture-slot ownership and VRAM
placement, loading schedule, each visual layer, object culling and camera bounds
together. A wider GPU output alone cannot reveal tiles the guest never loaded or
submitted. No field streaming code or map data is patched by this prototype.
