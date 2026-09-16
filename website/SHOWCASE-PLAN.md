# Feature display plan

Requested September 15, 2026: keep the visual feature displays, cut filler from
the copy, refresh older demonstrations and show more of the working features.

## Copy direction

Write for someone who knows Digimon World 2003 and wants to know what changes.
Name the feature, explain its effect, then let the capture demonstrate it.

- Use direct headings: “Adjust the grind” and “Travel from the map”.
- Give each paragraph one job. Cut repeated promises about adventure, discovery
  and returning to the Digital World.
- Describe controls and limits where they help someone decide or use a feature.
  Keep implementation details in the linked docs.
- Keep measurement scope and recording dates visible. Put detailed provenance
  here or in MEDIA.md instead of repeating it in every paragraph.
- Do not turn planned recordings into claims that the feature was just retested.

## Added in this pass

- A four-image widescreen gallery: card editor, Lab technique overview,
  Kumamon's locked-form hint, and Leomon's training menu.
- Images link to their full capture and use the existing pixel-preserving style.
- Existing GIF controls and the four-palette audible clip remain available.
- Gallery sources and limitations are recorded in [MEDIA.md](MEDIA.md).
- A selectable 4:3/16:9 Card Album comparison, using the verified September 15
  pair. It holds image height and pixel scale constant, with black margins in
  the original view. Native radio controls support keyboard and touch and work
  without JavaScript. The separate field/battle comparisons below remain queued.

## Refresh existing displays

These are queued recording/editing tasks, not finished assets. The current
September 11 GIFs and soundtrack clip stay dated until replacements are ready.

| Priority | Display | Replacement brief | Completion check |
| --- | --- | --- | --- |
| 1 | Portable Lab / evolution GIF | Record the current widescreen menu: open DIGIVOLUTIONS, select a partner, equip a form, load a technique, browse a locked hint. Split into short named clips if one becomes too long. | Show actual input and transitions; include an L1/R1 page turn and the native Cross glyph. No synthetic loading-speed impression from edited holds. |
| 1 | Soundtrack comparison | Re-record the same musical phrase across Original, DS, Sampled and Chip. Add Badlands and a battle track alongside Central Park once their instrument routing is reviewed. | Offer matched phrases for timbre comparison and a separate continuous hot-switch clip. Identical capture gain; no palette-specific post EQ or loudness normalization. Label area, revision and provisional routes. |
| 2 | Settings GIF | Focus each short clip on one decision: EXP/DV, encounters, screen view or battle motion. | Readable values and button feedback; distinguish demonstration values from defaults. Restore copied-profile preferences after recording. |
| 2 | Field/battle hero captures | Capture matched 4:3 and 16:9 views from the same state. Add a selectable comparison instead of just a wide screenshot. | Preserve image proportions and native pixel pitch. Do not crop a wide frame to fabricate the original view; disclose map-edge limitations. |

## Add new demonstrations

| Priority | Feature | What to show | Completion check |
| --- | --- | --- | --- |
| 1 | Memory-card loading and saving | A matched real-time before/after, including the progress bar and completion message. | Use copied cards and a recorded revision/configuration for each run. Time the same endpoints, distinguish data-transfer timing from the whole wait, and compare saved/loaded data. Do not animate the published numbers as a substitute for gameplay. |
| 1 | Battle motion | The same idle and action sequence at 100%, 150% and 200%, with the selected setting visible. | Keep whole-game turbo off. Show the camera too; pose completion can advance a script cue, so do not promise identical camera cue timing. |
| 1 | Map travel | Select a supported visited stop, confirm, and arrive; then show a blocked stop and its explanation. | Use a naturally visited copied save for the player demonstration. Identify any developer setup separately; avoid implying every map icon is supported. |
| 2 | Trigger shortcuts | L2/LT changing 4:3 to 16:9, then R2/RT starting and stopping turbo during normal play. | Label the logical buttons and retain a visible view/speed indicator. Reset turbo afterward. |
| 2 | Widescreen menu tour | Short clips of folder highlight pulses, card selection, Lab technique loading, gym/shop entry and return to the Start root. | Include full pulse cycles and opening/closing frames. The new still gallery remains useful alongside these clips. |
| 3 | Existing saves | Copy a DuckStation card into a separate profile and load it in Shinka. | Use sanitized paths and a copied card. Do not expose personal folder names or publish the card. |
| 3 | Minimized pause | Minimize and restore during a safe idle scene, paired with a small measured CPU trace. | Record the actual trace and explain that focus loss alone does not pause. No invented utilization figures. |

## Capture and delivery

Use an isolated copied profile. Keep the revision, settings, source frames,
timestamps and any measurement boundaries with the local recording. Publish
only the selected excerpts and update MEDIA.md with their source and treatment.
Do not publish saves, extracted banks, diagnostic dumps or entire music tracks.

Prefer short video for motion or timing. GIFs may summarize discrete menu views,
but must say when they are condensed. Start media only after a visitor action;
retain play/pause or play/stop, captions for settings changes, still posters and
responsive dimensions. Validate paths under the repository's Pages subdirectory.
