# Evolution tree in the field menu

## Accepted direction

Bring the Digimon Lab's evolution view into the field menu, with directional
hints for locked forms. Preserve the feeling that training and experimenting
reveal possibilities. Do not display numeric thresholds, completion percentages,
checklists of satisfied conditions, or an upfront list of every future form.

The exact placement and visual reuse still need a live inspection of the lab
view. The intended entry is within a selected partner's Status view, alongside
its existing evolution information. Keep the current partner selected on entry
and return to the same menu position on exit.

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
indicators. This visibility policy needs checking against the lab UI before
implementation and does not introduce a new persistent discovery flag yet.

## Current groundwork and integration work

`tools/evolution_hints.py` reads all 352 requirements (44 for each of eight
rookies) from the SHA-256-guarded original reward overlay and produces threshold-
free hint strings. Tests cover hidden names, numeric non-disclosure, two-form
requirements, independent rookie records and revision rejection. It is not
connected to the game menu yet.

The disc catalog contains `STGDGLAB.PRO`, 53,504 bytes at LBA 808, and localized
lab resource files named `*SDGLABO.BIN`. The reference's lab load address is a
placeholder, so it must be established in a live lab session. The field status
module already has a separately verified load address of `0x80082cb0`.

Before enabling the feature in the game:

1. Trace lab entry, selected partner, evolution-view state, resources and return
   path. Determine which code and assets can be reused by the field menu.
2. Confirm node visibility and obtain localized form labels through the game's
   own lookup. Pass only revealed names into the hint renderer.
3. Add the menu entry and hint panel with D-pad navigation, confirm and back,
   using the existing controller mapping. Ensure long labels and localized hint
   text fit the available panel.
4. Test opening/closing from multiple fields, switching partners, locked and
   unlocked forms, two-form requirements, and returning to gameplay without
   altering progress or leaving the wrong overlay loaded.

No gameplay requirements, rewards, saves or lab functionality are changed by
this groundwork. English clue wording is a draft; other supported languages
need their own text before enabling localized hint views.
