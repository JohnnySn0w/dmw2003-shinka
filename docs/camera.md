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
  shared gym/shop interfaces and the supported Status, card and Lab menus listed
  below, and anchors both expanded Start-menu roots to the wider canvas.
- **Battle zoom:** 100%, 90%, or 80% projected size. At 80%, the same viewport
  covers approximately 25% more world span along each axis. This changes the
  effective field of view; it does not move the scripted camera backwards.

They can be combined. Defaults retain 4:3 and 100%. Changes persist in the
existing mod state. L2/LT toggles the current supported scene's field or battle
view between 4:3 and 16:9 (keyboard default E). R2/RT toggles speedup (R).
See [trigger controls](controller-support.md#trigger-shortcuts).
Battle controls apply to ordinary battles (mode `0x600`);
the field preference applies to modes `0x200..0x2ff`, the gym (`0xa00`), shops
(`0xf00`), and the expanded Start root, Items, Sort, Map, Techniques, character
Status and Card Folders in the Status overlay (`0x1000`). Card Album (`0x1200`),
Edit Folder (`0x400`) and the Digimon Lab (`0xd00`/`0xd01`) also support the field
preference while their verified menu tasks are active. Card battles, movies and
rewards retain their original view. In battle 16:9,
enemy health, battle commands/submenus and bottom dialogue stay aligned on the
left; player health/MP and the miniature portrait move to the right. The bottom
dialogue panel spans between the outer edges of both health panels. Its text and
corner artwork keep their original size; technique MP costs follow the right
edge. Other HUD sizes remain unchanged. The 4:3 layout retains the original
positions and widths.

These are experiments, not a claim that every arena or cinematic was authored
for the expanded framing. Attack effects, arena boundaries, sky geometry and
game-side culling need coverage across more battles.

## Current screen coverage

| Scene | Preference and current behavior |
| --- | --- |
| Ordinary battles | **Battle**; wider arena view, side-anchored HUD and full-width bottom dialogue. **Battle zoom** is independent. |
| Overworld and interiors | **Field**; extra preloaded scenery where available. Authored map edges and object culling still limit coverage. |
| Both expanded Start roots | **Field**; party panels and menu/ribbon anchors follow the wider canvas, including return from a submenu. |
| Items, Sort, Map, Techniques and character Status | **Field**; supported panels, text and cursors move together. The map retains its native artwork width and cursor snapping. |
| Card Folders, Card Album and Edit Folder | **Field**; folder outlines expand as a unit; the editor grid stays compact and centered; the card picker has its own layout. |
| Physical and portable Digimon Lab | **Field** while verified Lab tasks are active; partner/form/technique screens, chart hints and L1/R1 page-turn ribbons have targeted alignment rules. |
| Shops and gyms | **Field** for the shared supported interfaces. Leomon and shop checks do not establish coverage of every NPC or training minigame. |
| Card battles, movies and rewards | Original view; not part of the widescreen conversion. |

The recent menu checks use the English game and a progressed copied save.
Selection pulses, opening/closing transitions and restored states have targeted
regressions, but they are not a guarantee for all menu owners or languages.
When comparing screenshots, let the menu settle and also check its transition;
these can use different native drawing paths. A chart title already stored in
an old savestate refreshes its button glyph when that chart is reopened.

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

## Verification history

The first battle-camera checks below predate the Field widescreen setting.
Their original 4:3 field/Status observations and test counts describe those
builds. Use [current screen coverage](#current-screen-coverage) for present
behavior; later dated sections record subsequent field and menu fixes.

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

The root uses the original encoded triangle button hint. Savestates from older
Shinka builds can retain the already-built text "Triangle: Close Status" or
"Triangle: Close Menu". The menu hook checks the ribbon child's copied string
for those exact retired labels and reruns the native label setters, preserving
the current row. It leaves other text and closing menus alone. Copied-state
checks covered restored roots in 4:3/16:9, repeated loading, Settings return,
and a fresh field root; native tests cover both legacy strings and rejection of
unrelated text/tasks and invalid buffer bounds.

Root anchoring also includes SETTINGS
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

### Character Status — 2026-09-15

The STATUS entry now stays wide through party selection, the stat summary,
equipment selection/comparison, digivolution selection, its action popup and
technique explanations. Stat numbers, names and cursors retain their original
size. Equipment rows stay together even below the usual description boundary;
the technique description and MP cost use opposite edges of a full-width panel.
The compact top header and fixed-pitch scrolling backdrop follow the shared
menu treatment. The native 4:3 option remains available.

The owner check recognizes `0x8008e744` with 68 children. Its last child is the
36-child digivolution controller (`0x8008b3c8`), which moves the stat block up
34 pixels when showing technique explanations. Both form selection and nested
techniques occupy root phase 21, so the renderer also validates this child,
its parent link and native slide range. It does not infer the page from old
text flags, which can remain set while their containing panel is hidden.
The field-to-overlay presentation guard includes row 4 while the verified
drawing rules still require live owners and the English layout signature.

Copied-save OpenGL checks cover Patamon and Angemon, the evolution action popup,
technique descriptions, equipment comparison, party selection and cancellation.
Captures at 426x240 and 320x240 are in `output/status-details-wide-01/` (ignored).
An additional 65 captures span field mode `0x24a` into the Status overlay
`0x1000`; all retain the 426-pixel viewport during that entry.
The 16 native suites pass, including owner reuse/invalid links, column alignment,
footer placement, joined panel strips and unchanged 4:3 packets in both framebuffer
bands. This does not establish coverage of every partner, equipment item or language.

The subsequent party-selection ribbon correction covers **Choose Digimon**.
Its nine 32px strips use palette `0x2697` at y=13 (cap UV `0x5fd4`, body
`0x8d20`), while the detail page uses the taller `0x7dea` header. Applying the
detail page's column anchoring to those strips split the ribbon behind the party.
The shared Start/Items ribbon transform now handles this variant before column
anchoring; its text also clears the intact angled cap. The party portraits retain
their left alignment. Copied-save captures in `output/status-ribbon-01/` reproduce
the original split and verify the correction, return from the summary, return to
the Start root, and live 4:3/16:9 switching. Native tests cover joined strip edges,
cap width, texture preservation, text/portrait separation and unchanged 4:3
packets in both framebuffer bands across all supported margins. All 17 native
suites pass with this correction.

### Map — 2026-09-15

The native map artwork is 392 pixels wide, so its full width fits inside the
426-pixel field view without stretching. The compositor centers that artwork
and cancels the native horizontal camera pan for the map, icons, selection
animation and free cursor together. Vertical scrolling remains native. The
location/travel tooltip stays at the left screen inset, and the shared moving
backdrop fills the narrow outer margins.

This is a rendering change: cursor coordinates, snapping, visited flags and
travel eligibility retain their native state. The live owner guard recognizes
the one-child map controller (`0x8009913c`), validates its callback prologue and
accepts only its known horizontal pan range, -72 through 0. Row 2 also joins the
field-to-menu aspect guard. The original 4:3 option remains unchanged.

Copied-save OpenGL checks cover both horizontal extremes, multiple animated
icon selections, unavailable travel from North Badland W and successful travel
from Central Park to Asuka's bridge entrance. Live 320/426-pixel switching leaves
the guest cursor and pan state unchanged. Captures and state snapshots are in
`output/map-wide-01/` (ignored). All 16 native suites pass, including every native
horizontal pan value in both framebuffer bands, unchanged sprite dimensions/UVs,
tooltip alignment and invalid-owner rejection. Other server maps and travel
routes were not separately verified in this pass.

### Card Folders and Digimon Lab — 2026-09-15

The field widescreen preference now includes the Card Folders entry menu, Card
Album, folder selection/editing, and the portable Lab's action/partner menus,
switching display, evolution chart, form selection and technique loading.
Backgrounds use the same fixed-pitch tiling as the other widened menus. Card
frames, artwork and selection highlights move by matching column offsets rather
than stretching the cards. Lab summaries stay left and action/list groups move
right. The chart keeps its connected node geometry centered, with title and page
controls at the edges. Folder-name entry retains a centered native-size keyboard
on the wide background.

The live owner checks distinguish these overlays:

| Screen | Mode | Callback / children |
| --- | --- | --- |
| Card Folders entry | `0x1000` | `0x80084a98` / 40 |
| Card Album | `0x1200` | `0x80085540` / 19 |
| Folder selector | `0x400` | `0x80089e98` / 27 |
| Folder grid | `0x400` | Selector child 0, `0x80086574` / 53 |
| Lab root | `0xd00` / `0xd01` | `0x8008ed0c` / 3 |
| Lab chart | Lab root child 1 | `0x800842f4` / 7 |
| Form technique overview | `0x800885ec` child 21 | `0x8008e8d0` / 28 |
| Technique loading table | `0x800885ec` child 23 | `0x8008c960` / 23 |

The folder selector sleeps in lifecycle 2 while its editor runs; the editor's
own live identity is required before applying its layout. The card-description
flag is editor `+0x43c`, toggled by original instructions at
`0x800857a0..0x800857b4`. It is separate from the animated `+0x68` field.
Description glyphs include a one-pixel baseline variation, so their whole text
band shares an anchor. The Lab's technique table similarly moves as a complete
unit; its footer expands while prose and MP cost use opposite edges.

Copied-save captures and packet/task snapshots remain local under
`output/folders-lab-wide-01/`. Checks cover album browsing, folder selection,
first/last grid-column highlighting, the sort prompt, explanation on/off, folder-name
entry, partner selection, switching display, chart hints, form technique lists
and the load confirmation popup. Matched state captures verify 320px and 426px
presentation for the grid, album, partner menu, chart and technique overview.
Native tests cover owner-chain reuse, language/transition guards, the sleeping
folder parent, distinct nested Lab slots, background strip joins, card/cursor
spacing, ribbon continuity, glyph baselines and unchanged 4:3 packets. All 17
native suites pass. This is English-layout coverage with the copied progressed
save; it does not certify every card, partner, physical-lab entry or language.

The portable Lab returns through native Status row 4 before its root constructor
restores DIGIVOLUTIONS (row 6). Presentation now recognizes the existing
`0x53484c42` return marker during that interval. All 54 sampled captures across
the chart → partner chooser → Lab actions → Start root sequence stayed 426px
wide after this correction. The two Card Folder return steps likewise retained
426px in their sampled captures.

### Menu entry and exit animations — 2026-09-15

The native menu builders switch from `SPRT` rectangles (`0x64`) to textured
`POLY_FT4` quads (`0x2c`) while scaling panels open or closed. The original
widescreen pass only handled the rectangles, so animated panels briefly used
their 4:3 placement. Position-based classification of an already shrunken panel
would also choose the wrong column.

The resident sprite and text builders now attach host metadata after completing
each animated packet (`0x8001f53c`, `0x80019e34`, including the text alias body).
It records the unscaled rectangle, native horizontal scale, pivot and verified
menu layout. The renderer applies the same layout used by stationary rectangles
and scales around the widened pivot. Translated icons retain their own centres;
resized panels and the shortened ribbon use the corresponding wide screen edge.
Native timing, vertical motion, textures, colours and guest packet RAM stay intact.

Metadata is bounded to 4096 recent commands with a direct source-word index,
compares all nine packet words before use, and clears on state restoration.
Capturing layout while building also allows already-built closing packets to
outlive their menu owner. Queuing another mode no longer disables a still-valid
Status/card/Lab owner chain; callback, language and lifecycle guards remain.
The shop/card full-screen semitransparent fade now covers the wide margins too.

Copied-profile OpenGL replays cover Status selection entry/exit, both Start root
views, card-folder return, Lab partner/action transitions, Leomon's training
menu and a shop exit. Sampled wide sequences stayed 426px; the original-view
Status replay stayed 320px. Local frames and packet traces are under
`output/folders-lab-wide-01/`. Native regressions exercise collapsed through
fully-open geometry in both framebuffer bands, a translated icon pivot, packet
reuse, state-reset invalidation, pending-mode ownership and fade coverage.
All 17 Shinka native suites (plus the dependency example), 189 Python tests and
Python lint pass. This covers the shared axis-aligned menu animation builders;
it does not certify every NPC-specific overlay or rotated/world primitive.

### September 15: Status details and folder-selection alignment

Both rows of the Status action prompt, their cursor, and the equipment/form
selection prompts now share a 24-native-pixel inset past the shortened ribbon's
diagonal cap. The base-partner tab in Choose Digivolve moves with the form list:
its frame, name and cursor use one right-hand anchor. The stat-sheet name below
retains its separate left anchor.

The folder selector's outline pulses through 16 palettes (`0x3c29`–`0x3fe9`,
stride 64). Matching only the initially captured `0x3d69` fixed one color state
but left most of the animation split. All five outline texture strips now use
the same continuous expansion in every palette state instead of splitting at
the generic left/right threshold. Folder
names follow the expanded panel's left edge with a four-pixel inset. These rules
also apply to the unscaled geometry captured for native menu animations.

Copied-profile captures cover both Status action choices, Choose Digivolve,
and folder 2 selected with 4:3/16:9 comparisons, plus Change Which One in
widescreen. Regressions
cover both framebuffer bands, margins 1–160, prompt/cursor movement, partner-tab
attachment, and shared outline endpoints. Captures remain local under
`output/folders-lab-wide-01/fixed-*`.

The pulse follow-up captures under `output/folders-lab-wide-01/folder-pulse-*`
include all 16 palette states across repeated cycles. The outline regressions
now cover every state on all three folder rows, including the diagonal join
and far-right strip, while preserving texture coordinates and name spacing.

### September 15: Card editing and evolution-tree details

The folder editor keeps its nine-column grid compact and centered inside the
widescreen background. Its last-row name/help panel uses the same coordinates
as the cards, including the top border at y=185. The editor's folder name has
the same four-pixel inset as the folder selector. The card picker has a separate
layout, identified by the live editor's child 52 (`0x800888b0`): its list,
cursor, name panel and description stay together instead of being treated as
independent card columns. The native staggered row-entry animation is retained.

In the Lab's form-technique overview, the plain strip at x=136 expands between
the stats and techniques. The x=168 strip contains the divider and moves with
the technique list rather than stretching away from it. Evolution-chart hints
stay centered as complete lines; only the exact shoulder-label baselines and
arrow textures anchor to the edges. Both arrows use all four pulse palettes
(`0x7d29` through `0x7de9`, stride 64).

The chart owner sleeps in lifecycle 2 during L1/R1 page turns. That verified
owner now retains the chart layout instead of falling back to the general Lab
layout and detaching the title cap. New chart titles encode the native blue
Cross glyph (`01 1b`) before “Hints”. Existing savestates containing an already
built title refresh it when the chart is reopened.

Copied-profile checks cover the compact editor, picker entry/exit, form-technique
overview, page turns, and Kumamon's two-line Kyubimon/partner-level hint. Local
captures and packet traces remain under `output/folders-lab-wide-01/`.
Regressions cover compact spacing, picker ownership, ribbon and shoulder
attachment, hint text across the old split threshold, and the technique-divider
join over both framebuffer bands and margins 1–160. This remains an English
layout check with the progressed save, not certification of every language.
