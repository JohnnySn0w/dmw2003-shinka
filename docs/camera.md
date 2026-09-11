# Experimental camera options

SETTINGS provides independent view and battle zoom controls:

- **Screen view → Battle:** 4:3 or 16:9. Native widescreen extends the horizontal rendering
  surface instead of stretching characters.
- **Screen view → Field:** 4:3 or **16:9 test**. The default is 4:3. The test
  reveals field scenery outside the original viewport without changing sprite
  proportions. OpenGL also draws preloaded tiles missing from the original
  submission. Unready or unsupported tiles can still leave incomplete edges.
  Small interiors can have authored black space outside their artwork. This is
  a preview, not a complete field widescreen conversion. It also widens the
  shared gym/shop interfaces, Items, Sort and Techniques, and anchors both expanded Start-menu
  roots to the edges of the wider canvas.
- **Battle zoom:** 100%, 90%, or 80% projected size. At 80%, the same viewport
  covers approximately 25% more world span along each axis. This changes the
  effective field of view; it does not move the scripted camera backwards.

They can be combined. Defaults retain 4:3 and 100%. Changes persist in the
existing mod state. Battle controls apply to ordinary battles (mode `0x600`);
the field preference applies to modes `0x200..0x2ff`, the gym (`0xa00`), shops
(`0xf00`), and the expanded Start root, Items, Sort and Techniques in the Status overlay (`0x1000`)
while their menu tasks are active. The lab, card battles, other Status children (including the
map), movies and rewards retain their original view. In battle 16:9,
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
updates presentation aspect, and shares a live scene predicate with the GPU.
Two wide scenes can change mode without briefly failing a cached exact-mode gate.
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

### Supplemental field scenery — 2026-09-11

The field owner preloads thirty tile buffers into main RAM while keeping twelve
tiles resident in VRAM. The missing edge cells observed during scrolling were
already among those ready buffers. The OpenGL implementation now decodes those
cells into private indexed textures, avoiding changes to the guest's temporary
list, tile residency, VRAM allocation, disc requests, or camera movement.

`src/field_tile_decode.c` bounds-checks raw and RLEN-compressed containers: three
rectangle lists followed by an 8-bit indexed TIM with a 256-color palette. Some
foreground pieces overlap the neighboring 128-pixel cell by one pixel. Palette
indexing, transparency and native field modulation use the existing GL shader.
`src/field_tiles.c` finds the active field owner from the live task tree and
checks revision, mode, camera callbacks, dimensions and ready flags. Only cells
outside the stock four-by-three window are supplemented. Their primitives join
the original three layer buckets in a separate double-buffered DMA arena.

Each prefetch slot has a content-checked texture cache. Save-state loads invalidate
decoded data and packet associations; restored supplemental packets are skipped
until valid data is prepared again. Software rendering and CPU-authoritative
dual rendering retain the earlier preview without supplemental textures.
`SHINKA_FIELD_TILES=0` disables supplementation for comparisons. The read-only
debug operation `shinka_nav` / `field-tiles` reports owner, cumulative prepared
frames, last-frame packet count and missing-cell count (cells outside the stock
window, including cells successfully filled).

Live copied-save checks filled Central Park's 21-pixel strip, including its
overlapping wall cap, and two additional edge tiles while moving through Wire
Forest Entrance. The same Central Park checkpoint with supplementation disabled
reproduced the strip; screenshots with it enabled filled it. Animated water and
characters differed in phase between captures, so this was not a pixel-identical
whole-frame comparison. Asuka Inn, battle, map, field width changes and restoring
a newly created edge checkpoint also rendered correctly. A developer warp to
Pelche Oasis rendered six supplemental pieces, but its navigation helper timed
out waiting for the quick menu; no traversal coverage is claimed for that warp.

All 15 native suites, 148 Python tests and Ruff passed. New native checks cover
raw/compressed truncation, repeat runs, invalid geometry and UVs, overlapping
pieces, packet links, double buffering, prefetch content reuse, state invalidation
and rejection in unrelated scenes. Local evidence is in
`output/field-stream-02/`. Coverage remains limited: untested tile formats,
NPC/object culling, native camera clamps, map boundaries and transition effects
still need investigation. Authored empty space in small interiors is preserved.

### Gym, shop and Start-menu layouts — 2026-09-11

The Field 16:9 preference now also covers the shared training overlay (`0xa00`)
and buy/sell overlay (`0xf00`). Their panels are tiled textured rectangles.
`src/menu_wide.c` expands panel and decorative background spans on the host;
glyphs, item icons and training images keep their original sizes and move as
columns. Shop description lines and the centered page counter retain their
spacing across the column boundary. Border artwork is widened with the panels.
The guest's packets, textures, selection coordinates and save data stay intact.

Both expanded Start roots anchor the party/currency panels left and the option
list/cursor right. The top instruction ribbon follows the visible 4:3 proportions:
its left tip sits 52 pixels before the plain root list, or 24 pixels before the
Items category list beside portraits. Its angled cap retains its original width;
only the plain body is shortened. Keeping the entire original ribbon exposed
artwork normally hidden behind the party and made the widescreen bar too long.
This includes SETTINGS
and the full-screen root reached by backing out of ITEMS. A validated pointer
from the resident menu callback gates those transforms; it is cleared on state
loads and rejected during another mode, queued transitions, teardown or the
map's close path. Only the root panel/font palettes are moved over a field.
Other scenery and NPC dialogue remain in their world positions. The Status
overlay also supports Items, but returns to 4:3 for its other children; widening the map, the lab,
card battles and remaining interfaces is still separate work.

Copied-save OpenGL checks covered Leomon's dialogue, training choice and TP
selector, exit back to Central Park, Gargomon's armory buy list/quantity and sell
categories/items, Wizardmon's item-shop list, both Start roots, SETTINGS, and
restoring checkpoints in these interfaces. These shops share the same overlay;
they do not need separate per-NPC patches. Other gyms and later-story merchants
have not been individually visited, and training minigames are not yet covered.

Native tests check both framebuffer bands, adjacent panel seams at every allowed
margin, original texture dimensions, glyph spacing, cursor anchoring, 4:3 and
unrelated-scene isolation, plus root lifecycle/state-reset guards. Local captures
and copied checkpoints are under `output/npc-wide-01/`.

### Items

The category selector, two-column inventory lists and item recipient chooser
now use the field widescreen preference. Party summaries and animated portraits
stay together on the left; categories and the compact instruction ribbon move right.
Inventory panels and the bottom description expand, while names, icons and
underlines retain their original sizes. The page counter stays centered and
the shoulder-button hints follow their respective columns. The selected-item
summary keeps its equipped and inventory counts in separate sections.

The guard follows four live task objects from the mode owner to the Items
callback (`0x80091d18`), validating callbacks, child counts, lifecycle, English
layout and overlay instruction signatures. It uses no RAM scan or retained
pointer across savestate loads. Other Status children cannot opt into this
layout merely by sharing mode `0x1000`. Only host drawing packets are changed.

Copied-save checks cover all five categories, a populated two-page item list,
recipient cursor movement, returning to the Start root, map isolation, checkpoint
restoration and live 4:3/16:9 switching. Native tests cover task reuse, malformed
child pointers, transitions, alternate languages, panel seams, texture sizes and
text anchors in both framebuffer bands. Captures remain local under
`output/items-wide-01/`.

The first pass recognized only one of the three 48×48 scrolling background
layers. The other two incorrectly followed the UI-column translation rule,
causing discontinuities as their tiles crossed the column boundary. All three
captured texture/palette pairs now use the same continuous horizontal mapping
in gym, shop, Items and both Start roots. The Start root previously omitted
these background textures from its drawing patch entirely.

Scrolling exposed a second problem: rounding each moving tile's left and right
edges separately alternated its destination width between 63 and 64 pixels at
16:9. That changed texture sampling during motion even when adjacent edges met.
The repeating background grid now rounds its tile pitch once (48 to 64 pixels
at 16:9), and all three layers share that pitch. Tile widths and texel sampling
stay constant through the 96-pixel scroll wrap. Only the repeating backdrop
uses this slight scale rounding; panels still match their exact screen edges.

The field-to-Items handoff uses the resident destination row, language and
previous field mode to retain the requested aspect while its task tree loads
or tears down. UI layout patches still require the verified live menu objects;
the recognized background tiles keep repainting the margins during teardown.
The native closing wipe is a separate five-column grid of 64×64 translucent
tiles using animated palettes. Its destination rectangles now span the full
viewport too, preserving texture dimensions, palettes and animation timing.
The Start root remains admitted through its closing phases and lifecycle 2,
including the final release-to-field handoff when cancelled. Confirmed submenus
stop admission at lifecycle 3; any actual mode change also ends it. Using input-ready
phases alone caused another narrowing when exiting with a non-Items row selected.
The GPU reads the same live scene predicate
as the frontend, avoiding an exact-mode gate mismatch between frontend updates.
The former eight-call latch expired during actual loading and was dependent on
renderer call frequency; it has been removed. Setting 4:3 takes effect immediately,
and unsupported Status destinations do not inherit a host-side widescreen latch
after a savestate load.
The fix leaves the panel and text layout unchanged. The native regression moves
every layer through the full scrolling range in both framebuffer bands and both
overlays, checking equal transforms and one/two-pixel steps without a boundary
jump. Consecutive live captures for the gym and armory are in
`output/npc-wide-01/scroll-fixed/`. Further transition and fixed-pitch scrolling
captures are in `output/menu-handoff-02/`: the before capture drops from 426 to
320 pixels twice during field-to-Items loading; the updated entry, Items-to-root
and root-to-field captures retain a 426-pixel viewport throughout. The native
tests additionally cover constant tile widths across every scroll phase, joined
wipe columns and their palette variants, immediate preference changes, and
unsupported destination/state-load isolation.

### Sort and Techniques

These pages share the party-card, ribbon and backdrop artwork with Items, but
have distinct task layouts. The same bounded owner-chain check recognizes
Sort (`0x800980b0`, 35 children) and Techniques (`0x80096380`, 45 children)
in the controller's second slot, like Items. The first slot holds the Start root
when returning from a page. Each check
also validates the callback prologue, lifecycle, English layout and parent tasks.

Sort keeps the complete party cards on the left, including selection highlights
and the two-step swap UI. Techniques keeps its list tab, border, names and cursor
together on the right. Both use the full-width description panel and compact
instruction ribbon. Technique descriptions stay left aligned, while the MP cost
follows the right edge. Shared background and wipe handling preserves the new
aspect while loading or returning to the root. Unknown Status children still
use 4:3; merely selecting a row does not authorize their drawing layout.

Local captures and diagnostic task/packet snapshots are under
`output/status-wide-01/`. Copied-save checks include swapping Patamon and Guilmon,
the linking arrow, no-technique messages for Kumamon and Guilmon, and Small Heal
restoring Patamon from 100 to 884 HP while spending 16 MP. The test-only HP change
was made in the copied session. Confirmation, cancellation and return to the
correct root row were checked, along with live 4:3/16:9 switching and map isolation.
Field-entry captures for both new pages remain 426 pixels wide throughout loading.
Native regressions cover first/second child-slot
isolation, malformed task chains, callback reuse, language/signature guards,
list-tab and cursor alignment, party-card anchors, and MP/description separation
in both framebuffer bands at every supported margin.
