# Evolution tree in the field menu

## Accepted direction

Bring the Digimon Lab's evolution view into the field menu, with directional
hints for locked forms. Preserve the feeling that training and experimenting
reveal possibilities. Do not display numeric thresholds, completion percentages,
checklists of satisfied conditions, or an upfront list of every future form.

The first implementation opens the original chart through Square on STATUS in
the field menu. It asks which partner to view and returns to Status's partner
selection on exit. Direct entry from an already selected partner, retaining that
selection on return, remains a refinement.

Hints come from that rookie's own requirement table. A form can have different
requirements for different partners; a global hint attached only to the final
form would be misleading.

## Hint wording

| Requirement family | Proposed player-facing hint |
| --- | --- |
| Rookie growth | Grow stronger alongside your partner. |
| Known prerequisite form | Deepen your mastery of Greymon. |
| Unrevealed prerequisite | Explore other evolution paths with your partner. |
| Strength | Develop greater strength. |
| Defense | Build your physical defenses. |
| Spirit | Strengthen your spirit. |
| Wisdom | Cultivate your wisdom. |
| Speed | Develop your speed. |
| Machine affinity | Train your affinity with machines. |
| Other elemental affinity | Train your affinity with fire/water/ice/wind/thunder/darkness. |

For a two-form prerequisite, describe training both forms, without suggesting
that using the DNA battle attack unlocks the destination. Do not recommend
fighting a particular enemy type unless that behavior is actually relevant to
the requirement. Affinity clues direct the player toward training.

Keep deeper undiscovered names hidden unless the existing lab's discovery
policy already reveals them. Use a silhouette or an unknown node as appropriate
to the eventual view. Selecting a locked node displays its clues; discovered
forms retain their identity. Unlocks remain surprises without numeric proximity
indicators. The inspected early-game lab chart uses question marks for locked forms and
shows four pages. Deeper-path visibility still needs a progressed save. This
feature does not introduce a new persistent discovery flag.

## Experimental menu connection

Enable with `python tools/configure_journal.py --enable`, then restart. Disable
with `--disable`. The PowerShell launcher accepts `-EvolutionJournal` or
`-EvolutionJournal:$false`. The option is independent of normal and DV EXP.
Fresh configurations leave it disabled; the current local test setup enables it.

In an English field menu, highlight STATUS and press Square. Choose a partner
with left/right and X. Use the original D-pad and L1/R1 chart controls. Triangle
returns to Status; back out of Status normally to resume exploration. The
shortcut exposes chart viewing, with switching partners and equipping forms
remaining in their existing menus. The source is `src/journal_menu.c`.

Directional clues are **not rendered in the game yet**. The requirement reader
and formatter in `tools/evolution_hints.py` cover all 352 original requirements,
with tests for hidden names, two-form requirements, per-rookie differences,
numeric non-disclosure, and revision rejection. Connecting these strings to the
highlighted locked node is the next feature step.

## Verified integration points

The complete original `STGDGLAB.PRO` (53,504 bytes, LBA 808, SHA-256
`3dec8fc81a7db98010b8f10cc9bd9cc06f5b09216885f6f9ce1e79e088d6de59`)
matched live lab RAM at `0x80082cb0`. Status uses that same address. The native
module dispatcher owns the replacement and teardown; the menu must not call
across these overlays while one is still executing.

- `0x8004b3f8`: active stage; `0x8004b3fc`: queued stage.
- `0x80016b88`: resident stage setter; `0x80016b28`: queue consumer.
- `0x80055d28`: loaded module index; `0x80055ccc`: module file-index table.
- Lab is stage `0x0d00`, file index 492, constructor `0x80083040`.
- Status is stage `0x1000`, file index 519, constructor `0x80083654`.
- `0x80048d68..0x80048d77`: cached field mode, position and facing used on return.
- The quick-menu task is `0x8001270c`; its selected row is at object offset
  `0x58`, with STATUS at index 4. Its existing transition call returns to
  `0x80013334`.

The shortcut runs that normal menu close sequence before changing the queued
stage to a dedicated `0x0d01` journal variant. This matters: directly queuing the
lab from an arbitrary field left the return context pointing to the previous
area in the first diagnostic experiment. That experiment was discarded.

The journal variant selects the chart through the original action-panel close
animation. Its guarded callback table permits only chart viewing while this
variant is active. When the chart task finishes, four guest instructions queue
Status through the resident setter. The normal lab variant retains its original
callbacks. All code sites are checked before any are changed, including after
savestate loads; unsupported overlay bytes are left alone.

Two small hooks are added to generated copies of the game code by
`tools/journal_hooks.cmake`. The pinned dependency and original generated files
remain intact. Explicit frontend registration is necessary because the pinned
framework's unused C CRT constructor was removed by this MSVC release build.

The English menu prompt replaces one string within its existing 28-byte
allocation. Its disc patch is revision-guarded. A matching cached resource is
also updated because pre-feature savestates may already contain the old text.
Other languages retain their original menu behavior.

## Coverage and remaining work

Local live checks use `output/menu-test-saves`, a copy of the diagnostic saves.
The original player memory cards are not used for these checks. Captures and
extracted game data stay ignored.

Live verification covered opening from Asuka Bridge and Central Park; Kumamon,
Guilmon and Patamon; all four pages; cancelling the initial partner chooser;
saving/loading a state within the chart; returning through Status to the same
Central Park position; and the normal lab's Switch Digimon screen. The menu
prompt was visually checked on an older savestate. The known original card hash
remained unchanged. These early-game checks do not establish campaign coverage.

For repeatable navigation to the physical lab: enter Asuka City's Main Lobby,
take the right staircase down, then use the lower southeast branch around the
shrub and along the zigzag corridor. The upper thin walkway leads to the Login
Room. Face the transition and press X; walking into it alone does not enter.
Diagnostic slot 9 is the lab entrance and slot 7 its action menu in the copied
menu-test save directory.

The new native regression test checks inactive-package behavior, unrelated menu
and transition guards, the guest-state entry marker, field-context preservation,
unknown-overlay rejection, and restoration of the normal lab callbacks. Python
checks cover mod-state changes without disturbing the EXP options. The build
script runs both Shinka native tests rather than unrelated dependency examples.

Before promoting this developer feature, expand coverage to progressed parties,
locked and unlocked branches, unlocked chart pages, all field families and languages.
Add selected-partner retention and the directional hint panel. Map teleportation
and encounter settings are separate outstanding features.
