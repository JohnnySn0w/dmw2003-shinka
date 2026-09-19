# Paused work — September 16, 2026

This is the historical September 16 pause snapshot. Work resumed September 19.

## September 19 update

The music-label notebook was restarted on localhost port 62006 with the existing
label file and native Badlands captures. Square backdrop repetition is now
implemented for Status, Lab, card, shop and gym menus; see the September 19
section of `camera.md`. Consecutive recordings under `output/menu-square-01/`
show simultaneous diagonal motion, including a pixel-exact patch across the
left framebuffer join during Status backout. The final perceived pinch still
needs user confirmation. Compact detail sheets and the parent lifetime fix
remain included. All 19 native tests, the two capture-parser tests and Ruff on
the new Python tool/tests pass. The notes below describe the starting state,
not the current implementation.

## Completed locally, not yet committed

- The full lower stats/skills sheet keeps its original width and is anchored to
  the right in Status > See Digivolve and the Lab form-selection layout shared
  by Load Technique and Change Digivolve Type. This corrects the prior change
  that narrowed stats but left an excessively wide skill list.
- The top-left partner panel retains its layout during the one-frame interval
  when Status child 67 is being constructed or released. Consecutive captures
  reproduced the jump before the fix and show it staying anchored afterward.
- Added an opt-in `menu_capture` debug command and Python exporter for up to
  180 consecutive display frames, avoiding gaps from screenshot polling.
- Updated geometry/lifecycle tests and camera/developer-navigation docs.

All 19 native tests and the two new Python capture-parser tests passed. Ruff
was not run: it is not installed in the bundled Python environment or on PATH.
The normal Release executable was rebuilt with these local changes. No game
process was running at the pause check.

The Lab Load Technique form sheet and actual technique picker were visually
checked. Attempting Change Digivolve Type for the selected Patamon returned
"Can't change digivolve"; its shared layout is covered by code/tests, but an
available Change Digivolve Type selection still needs a visual check.

## Still open

### Widescreen backgrounds: stretched tiles and uneven motion

Latest user report: all widescreen menu backgrounds turn square tiles into
rectangles, with jagged movement that feels like alternating x/y steps.

`src/menu_wide.c` currently widens 48-pixel backdrop tiles to 64 pixels at the
standard 16:9 margin. This confirms the aspect distortion and makes horizontal
motion advance at a different scale from vertical motion. It is not yet proof
of the entire perceived stutter's cause.

**No background fix has been implemented yet.** Proposed next step: preserve
48x48 geometry and original x/y motion, repeating the native pattern into the
extra horizontal space instead of stretching it. Captured Status backdrop
packets suggest a 96-pixel horizontal pattern period. Verify that assumption
for each texture family before applying it across shop, gym, card and Lab menus.

A possible implementation is a bounded host-side repeat helper in
`src/menu_wide.c/.h`, invoked from the textured-rectangle GPU path through
`tools/view.cmake`. Keep palette, UVs, draw order and 4:3 behavior intact. Never
edit the pinned emulator dependency directly. Existing backdrop tests assert
stretched widths and must be replaced with square-tile coverage, phase/wrap,
framebuffer-band and guard tests. Check consecutive animation frames, not just
stills, including both sides of the native/wide framebuffer join.

### Whole-screen pinch: partner chooser -> root menu

The user identified this exact backout transition and clarified that the
background also distorts. It remains unresolved. Presentation records stay at
426x240 with a stable destination rectangle. Consecutive captures show a
background join mismatch near the 53-pixel left margin in some frames.
Disabling automatic backdrop stretching or the center-copy optimization did
not resolve it. Temporary diagnostic toggles/traces were removed; do not claim
that the parent-panel fix resolves this separate issue.

Recheck this transition after implementing square background repetition.

## Files and evidence

Implementation changes: `src/menu_wide.c`, `src/journal_menu.c`,
`src/menu_capture.inc`, `tools/dev_nav.cmake`, `tools/export_menu_capture.py`.
Tests: `tests/test_view.c`, `tests/test_journal_menu.c`,
`tests/test_menu_capture.py`. `src/view.c` is also marked modified by Git;
temporary tracing was removed, so inspect its diff/line endings before staging.

Ignored local evidence lives under `output/menu-compact-03/`:

- `portrait-in.png` versus `portrait-fixed.png`: one-frame parent-panel jump.
- `final-status.png`, `final-lab.png`, `lab-load-tech.png`, `lab-43.png`:
  compact-sheet and picker comparisons.
- `final-detail-in.bin`, `final-detail-out.bin`: final consecutive captures.
- `fresh-backout.bin`, `fresh-backout-contact.png`: chooser-to-root transition.
- `compositor-ab.png`: backdrop/center-copy diagnostic comparisons.
- `launch.json`: isolated diagnostic launch arguments (port 4384).

Debug capture example:

```json
{"cmd":"menu_capture","frames":120,"path":"ABSOLUTE_PATH.bin"}
```

Export with `tools/export_menu_capture.py INPUT.bin OUTPUT_DIRECTORY`.
Record before pressing the transition button and wait for `active: false`.

Isolated save-state slots in that output's copied profile: 3 = Status partner
chooser, 4 = full-background root menu, 5 = Status summary, 7 = See Digivolve,
8 = Techniques, 9 = Lab Load Technique form picker, 0 = actual technique
picker. Slot 2 was overwritten with the Lab action menu. Do not overwrite or
test saves in the user's live profile.

## Repository and next delivery

HEAD and origin/main were `41f7af2` at pause. Earlier `c675118` and `41f7af2`
were pushed; this note's completed local work has not been committed or pushed.
The user has authorized pushing tested work to main. Pause takes precedence:
no further build, game testing, commit or push was performed after the request.

Preserve unrelated untracked files: `assets/shinka_new.png/.xcf`,
`assets/shinka_test.png/.xcf`, and `starvation_dump.jsonl`.

On resumption: inspect the working diff, implement/verify native square
backgrounds, recheck the unresolved transition, run relevant tests and lint,
update documentation to match the evidence, then commit/push only reviewed
project changes. Report any remaining visual uncertainty explicitly.
