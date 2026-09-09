# Random encounter settings

The English expanded menu provides **SETTINGS → Encounters** with 0%, 50%, 100%,
150%, and 200%. Left/right or confirm cycles the value. The default is 100%.
Changes persist in the existing mod package state and take effect at the next
eligible movement check. Disabling the expanded-menu feature restores the normal
rate on the next eligible check. Restart after enabling or disabling that feature.

At 0%, movement stops consuming the remaining random-encounter countdown. Resuming
uses that remaining countdown; it does not accumulate missed encounters or draw
extra random numbers. An encounter already queued before opening the menu still
loads. Scripted encounters have a separate entry point and are not suppressed.

## Original calculation

The supported European `FIELDSTG.PRO` loads at `0x80082cb0`. Random encounters use
`0x80092664`; scripted encounters enter at `0x800927a0`. The random path runs on
eligible player movement, resolves terrain, then deducts one of six terrain costs
from the resident countdown at `0x80048d64`. Expiration launches a random battle
when the game's encounter-enable word at `0x80042b1c` is nonzero. Standing still
does not consume the countdown.

The reset function at `0x8009252c` calls the existing RNG. With
`r = RNG % 2304`, the next countdown is `r` when `r < 256`, otherwise
`floor((r + 256) / 2)`. Its range is 0–1279. The slider changes movement costs,
retaining the original roll, terrain differences and encounter selection.
Individual battle spacing therefore still varies.

For non-default settings, the countdown uses half-point units: twice the original
countdown, with each original terrain cost multiplied by `rate / 50`. This keeps
50% and 150% exact even for odd terrain costs. Returning to 100% rounds any remaining
half-point upward, an adjustment of at most half an original countdown point.
At 0%, a zero seed is held at one half-point so it cannot expire while paused.

## Integration and state handling

`src/encounters.c` hooks the random path's actor lookup and the reset's existing
RNG call, validating their exact return addresses. It verifies the field overlay's
function pointers, all 157 words covering reset/selection/check code, and the six
terrain costs before modifying data. Costs must match the complete original table
or the complete recognized scale; unknown revisions or mixed tables are rejected.
The local build derives comparison data from the owner's hash-verified disc.
The generated header is ignored and must not be distributed.

Writes are confined to the countdown, its enable word and the six terrain costs
at their original RAM address. No executable instruction or RNG result changes.
The enable word retains its nonzero meaning while its upper bits track the scale
and whether the current countdown is doubled. A native zero flag stays disabled.
The reset hook clears the doubled marker before the original function stores a new
roll, including when the next battle is already queued.

All countdown state and table values live in serialized game RAM. No host cache
or temporary enhancement allocation owns this state. This matters because the
pinned runtime does not serialize enhancement memory. Opening a full-screen menu
can replace the field overlay; the resident scale marker survives and the next
movement check reconstructs the terrain costs without doubling the countdown
again. On state load, the saved calculation can finish using its saved costs;
the current persisted option is applied at the next complete movement check.
The original table address remains valid even if a saved CPU register already
holds that address.

## Verification and limits

The native encounter test covers every rate across all six terrain costs, unchanged
100% behavior, long pauses, zero seeds, rate changes, repeated resets, queued battle
resets, old and modified state restoration, overlay replacement, feature disabling,
scripted-call rejection and allowed write locations. The menu test checks the fourth
row, encounter changes independent of EXP, and BACK returning to SETTINGS.

Live fixed-route tests compare the countdown directly, avoiding a noisy estimate
from a handful of battles. They verify exact 0%, 50%, 100%, 150% and 200% deductions,
a long pause, entry into a random battle at 200%, and the subsequent counter reset.
A modified state preserves its countdown and costs across a complete process
restart. Both menu roots show the four rows; restored SETTINGS labels follow the
persisted option. Returning from full-screen Status to the field restores 100%
units and terrain costs on the next movement check.
Private save-specific records and screenshots remain outside Git. These checks
do not establish full campaign or boss coverage; the unchanged scripted path is
supported by code tracing and guarded-call tests.
