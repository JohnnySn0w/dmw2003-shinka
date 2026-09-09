# Expanded field menu

The optional English field menu adds **DIGIVOLUTIONS** and **SETTINGS** after
the original entries. Card Folders keeps its original availability rule: there
are seven rows before it unlocks and eight afterward. Enable with
`python tools/configure_journal.py --enable`, or launch with `-EvolutionJournal`.
Restart after changing that feature selection.

Use the existing D-pad and confirm/cancel mappings. DIGIVOLUTIONS opens the
original lab chart and partner chooser. Triangle returns through Status, as in
the previous prototype. Square on STATUS is no longer the entry point.

SETTINGS has three rows:

- **EXP:** 1x, 2x, 3x, 4x normal battle EXP, before participation splitting.
- **DV EXP:** 1x, 2x, 3x, 4x final DV EXP, or fixed 10 points per participating form.
- **BACK:** return to the field menu. Triangle also returns.

Left/right cycle a value; confirm also advances it. Each successful change is
saved using the existing mod package state and applies to subsequent battles
without restarting. The screen reports a save failure and retains the previous
settings if validation or persistence fails. The current local selection is
3x normal EXP and fixed 10 DV points. Encounter adjustment and map teleportation
remain separate, unimplemented features.

## Implementation

The menu is not one flattened image. `0x8001270c` runs a task with separate text
children, a cursor, party panels and an independently drawn tiled background.
The original already chooses five or six rows according to Card Folders access.

`src/menu_list.inc` expands the task from 0xa0 to 0xa8 bytes and its child-pointer
array from 0xac to 0xb4. Original child offsets remain intact. Rows 6 and 7 live
at child offsets 0xac and 0xb0; three guarded generated memory accesses handle
these appended slots. The existing destructor owns all children. The two extra
task words store the page and the displayed settings/error state, including in
savestates. The original text setters allocate and copy each encoded label.

The background renderer receives a small dynamically constructed sprite
descriptor. It copies six tile definitions from the loaded game resource and
adds whole 14-pixel rows between the original top and bottom tiles. Borders and
horizontal separators retain their original pixels. SETTINGS uses three rows.
Transient text and sprite descriptors use the runtime's enhancement memory;
they are rebuilt when a restored state lacks them.

`tools/generate_menu_hooks.py` adds verified entry hooks and row accesses to
copies of the locally generated CPS code. The original output and pinned
framework checkout are untouched. CMake similarly builds a copy of the pinned
mod runtime with `src/menu_settings_bridge.inc`, exposing only the validated
EXP options to the emulator thread. The normal launcher/CLI state remains the
source of truth; no second settings file is introduced.

The committed disc-read plan handles future loads. `src/menu_exp.c` also
updates matching live and prefetched reward overlays, including on savestate
restore. It validates immutable calculation code, every DV/BIT table cell,
recognized EXP factors and recognized DV instruction variants before writing
anything. Values are always derived from the original table, so repeated
changes cannot compound multipliers. Code writes invalidate stale compiled
paths through the runtime's executable-RAM API. The private comparison header
and EXP manifest are generated from the verified local disc during the build
and remain ignored by Git.

## Compatibility and verification

Older savestates with a menu already open retain the old layout until it is
closed and reopened. Newly created menus use the expanded allocation. Restoring
a state inside SETTINGS refreshes its labels to the current persisted rates.
Loading an expanded-menu state with the feature disabled retains safe child
addressing and teardown while hiding the added actions.

Testing uses copied diagnostic saves, not the player's original cards. Native
checks cover child-slot boundaries, input routing, chart transitions, overlay
revision rejection, normal-lab restoration, all 20 normal/DV rate combinations,
live and prefetched copies, idempotence and restored reward data. See
`docs/evidence/expanded-menu-checks.json` for live observations. This remains an
English early-game feature; other languages, later areas, campaign progression
and physical controller devices have not received equivalent coverage.
