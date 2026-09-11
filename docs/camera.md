# Experimental camera options

SETTINGS provides independent view and battle zoom controls:

- **Screen view → Battle:** 4:3 or 16:9. Native widescreen extends the horizontal rendering
  surface instead of stretching characters.
- **Screen view → Field:** 4:3 or **16:9 test**. The default is 4:3. The test
  reveals field scenery already submitted outside the original viewport, without
  changing sprite proportions. Scrolling can expose blank or incomplete strips
  at the edges because the guest's tile loader still covers the original view.
  Small interiors can have authored black space outside their artwork. This is
  a preview, not a complete field widescreen conversion.
- **Battle zoom:** 100%, 90%, or 80% projected size. At 80%, the same viewport
  covers approximately 25% more world span along each axis. This changes the
  effective field of view; it does not move the scripted camera backwards.

They can be combined. Defaults retain 4:3 and 100%. Changes persist in the
existing mod state. Battle controls apply to ordinary battles (mode `0x600`);
the field preview applies only to modes `0x200..0x2ff`, including the field quick
menu. The lab, card battles, full-screen menus, movies and rewards retain their
original view. In battle 16:9,
enemy health, battle commands/submenus and bottom dialogue stay aligned on the
left; player health/MP and the miniature portrait move to the right. The bottom
dialogue panel spans between the outer edges of both health panels. Its text and
corner artwork keep their original size; technique MP costs follow the right
edge. Other HUD sizes remain unchanged. The 4:3 layout retains the original
positions and widths.

These are experiments, not a claim that every arena or cinematic was authored
for the expanded framing. Attack effects, arena boundaries, sky geometry and
game-side culling need coverage across more battles.

## Implementation

`src/view.c` separates persisted preferences from the effective scene settings.
`src/view_frontend.inc` configures the pinned runtime's native-wide compositor,
updates presentation aspect, and gates gameplay presentation on the current scene
mode. Its change detector includes the mode itself: two wide fields with different
area IDs must update the exact-state gate even though both use 16:9.
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

The dialogue extension recognizes its native six-piece textured panel. It
preserves the two end caps and stretches only the four middle strips through
the renderer's scaled-rectangle path. Integer boundary calculations leave no
gaps between pieces. Dialogue text stays left anchored even on long second
lines; the MP-cost font is identified separately from ordinary prose.

Debug tooling uses `shinka_nav` operation `view`. With no arguments it reports
stored width/zoom and effective wide/percent values. To persist a choice, supply
`option: 0` (battle width, values 0..1), `option: 1` (battle zoom, values 0..2),
or `option: 2` (field preview, values 0..1), plus `value`. The report's `field`
member is the stored field preference; `active_wide` is the effective scene state.
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

### Dialogue indicator pulse correction — 2026-09-10

The dialogue advance indicator previously jumped horizontally during its pulse.
It uses a fixed 12x12 sprite at (291,208), UV `0x3c54`, with five changing CLUTs:
`0x3057`, `0x3097`, `0x30d7`, `0x3117`, and `0x3157`. The initial alignment rule
recognized only `0x30d7`; other pulse phases inherited left-aligned text placement.
The fix recognizes all five palettes while retaining the exact position, UV and
size checks. Palette animation itself remains unchanged.

The issue reproduced with native battle optimization disabled. After rebuilding,
24 live screenshots with it enabled covered all five palette variants: every
image showed the marker at the outer right anchor and none at the old position.
Regression checks cover every palette, both framebuffer bands, margins 1..160,
unchanged 4:3 placement, and rejection of unrelated textures/palettes. The view
suite passed. Local packet and screenshot evidence is in ignored
`output/dialogue-indicator-01/`.

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

### Opt-in field preview — 2026-09-11

The owned renderer now exposes the already-submitted tile overhang at 426x240.
The Screen view submenu has separate Battle and Field preferences, clears the
unused rows when opening, and returns the highlight to Screen view. Battle zoom
remains a separate SETTINGS row. Page 6 is used for the new submenu; page 5 stays
reserved for the map's stock close path. A new settings fingerprint bit prevents
an old saved menu page from overwriting the current field preference.

Live OpenGL tests with copied cards/checkpoints covered Central Park, Asuka Inn,
and Wire Forest Entrance, ten moving Central Park captures, field-to-field state
loads, a Kunemon battle, the map, and controls in both menu roots. The native
view was 320x240 with the preview off and 426x240 with it on. Field projections
stayed at 100% while the battle retained its separately selected 80% zoom. The
map retained 320x240. A Central Park scrolling capture exposed a 21-pixel blank
strip at the left edge, confirming that renderer-only expansion is incomplete.
No claim is made for all maps, NPC visibility, cutscenes, or transition effects.

All 14 native suites, 147 Python tests, and Ruff passed. Native checks cover both
width preferences independently, field-range boundaries, boot/menu/movie/save
scene isolation, unchanged battle HUD behavior in fields, both settings roots,
persistence failure, and saved-page preference reconciliation. The installed
build was smoke-tested at the default 4:3 field view with the new submenu; player
settings and original memory cards were not changed. Captures and scene reports
are local under `output/field-wide-01/`.

The next step is expanding the field tile working set, including its temporary
list and residency/VRAM scheme, then testing scrolling, object culling, and
camera bounds. Merely raising the four-column loop limit is not sufficient.
