# Map travel

The experimental English expanded menu supports **X to travel** from the original
map. Move the cursor until it snaps to an icon. Eligible locations show
**X: Travel** beneath their original name (**X: City entrance** for Asuka).
Confirm cuts directly from the map to black, then uses the original field loader
to arrive. It does not reopen the
Status root or play its closing animation. The original destination title card
and loading sequence remain. Triangle without confirming closes
the map normally.

The initial travel network connects these Asuka locations:

| Map icon | Arrival |
| --- | --- |
| Asuka City | Bridge, outside the plot-dependent Main Lobby entrance |
| Central Park | Paved plaza |
| Wire Forest Entrance | Open path |
| Wire Forest | Clearing near the path |
| Seiryu City | Outdoor city path |
| South Station | Walkway beside the gondola controls |
| Bulk Swamp / Bulk Bridge | Bulk Bridge's wooden crossing |
| Tranquil Swamp | Boardwalk near the inn |
| Phoenix Bay | South-side bridge, or northern approach while its earthquake event is pending |
| Pelche Oasis | Path near the waterfront |

The exact arrival area must already be visited in the loaded game. One icon can
represent several rooms, so having the icon visible is insufficient. If you are
already in the arrival field, it shows that status instead of offering travel.

Travel currently starts from these same fields, plus Asuka Main Lobby and Bulk
Swamp. Bulk Swamp shares an icon with Bulk Bridge, but only visiting the swamp
does not unlock the bridge landing.
Other interiors, dungeons, other servers and unvalidated late campaign states
show an unavailable message. There is no cross-server map switch. The build
accepts story word values 1–36 for this initial network; this is a conservative
validation boundary, not a claim that every later value denotes post-game.
Broader campaign coverage, additional arrival points and post-game routes remain
work to do. Existing map navigation and visibility rules are preserved.

After the Seiryu badge, travel out of Seiryu shows **Use the city exit** until
Teddy's Wind Prairie conversation finishes. Returning to Seiryu remains allowed.
Asuka uses the outer bridge approach while Keith's early encounter is unfinished,
then resumes its usual bridge landing. Both arrivals remain outside the city
entrance, preserving the original gate during the later lockdown.

The three South Sector stops require the original South Station arrival scene to
finish and the station to have been visited. Every landing also needs its own
visit. **Finish the gondola trip** or **Visit South Station first** explains a
missing prerequisite. This policy applies to departures as well as arrivals,
including departure from Bulk Swamp, where the first arrival scene leaves the
party. The gondola interior, Jungle Grave, Suzaku and the inn/shaman interiors
remain outside this travel network. Phoenix Bay is now a surface destination once
its exact field has been visited. Jungle Grave remains excluded because its first
entry owns the Zanbamon encounter and returns the party through the native event.

Most unsupported icons currently mean that no arrival point has been validated;
they do not imply a known story lock. The story range above is a broad scope
limit, not a complete quest-by-quest access policy. Earlier visitation does not
prove current access: travel could bypass a scripted entrance, escape a gated
sequence, or reach an area whose NPCs depend on another story phase. Each added
route needs those checks as well as a valid landing position. Leaving quest flags
unchanged is necessary but does not by itself establish sequence safety.

Enable the expanded menu with `python tools/configure_journal.py --enable` and
restart. A savestate with the old Status allocation says **Reopen menu for travel**;
close the whole menu and open it again. EXP, encounter settings and the portable
lab remain described in [field menu controls](field-menu.md).

## Implementation

The original `STSTATUS.PRO` is 100,936 bytes and loads at `0x80082cb0`.
`tools/generate_map_data.py` validates its SHA-256 and generates private comparison
data for the selection, rendering, controller and visitation routines. This
header comes from the owner's disc and remains excluded from Git.

The map task callback is `0x8009913c`. Its `+0x180` word records whether the cursor
is snapped; `+0x184` is the selected one-based icon. The original hit test accepts
cursor coordinates inside the icon's inner rectangle and considers the map's
visibility cache at `+0xa8`. Travel consumes this result rather than implementing
a second cursor or hit test.

The stage-to-icon table starts at `0x8009b5fc`. The original map groups visited
fields by icon using the flag accessor `0x800163b0`. Field visitation is recorded
in the bitset at `0x8004b3c0`, indexed by the stage's low byte. Travel additionally
checks the specific destination bit, current server/source, language, story
boundary, lifecycle and complete guarded code/data ranges. The story value at
`0x8004b370` is a 32-bit word, matching the original field scripts. Seiryu's
departure guard checks story 5 and flag `0x4011` clear (`0x8004b3e0`, mask `2`).
Asuka's alternate landing checks story 6 and flag `0x4016` clear (the same byte,
mask `0x40`), choosing `(0x27e34, 0x12bcc)` instead of `(0x2dda8, 0xf760)`.
Original-script evidence is recorded in the [story audit](travel-story-audit.md).
South travel additionally requires story `7..36` and the exact visit for `0x232`
(`0x8004b3c6`, mask `4`). Its guarded sources are `0x232`, `0x233`, `0x234` and
`0x237`; only `0x232`, `0x234` and `0x237` are arrival points. The arrival scene
in `WSTAG440.PRO` advances story `6` to `7` before the party enters Bulk Swamp.

`src/map_travel.c` extends the Status controller body from 0x78 to 0x88 bytes,
storing a pending marker, icon, source and story snapshot. Its child array gains
one null slot; the resulting child count identifies the new allocation without
reading past old savestate allocations. The existing destructor owns every child.
All pending travel state is serialized in game RAM. Host-side memory stores only
temporary text that the original text setter copies into its own allocation.

On confirm, the map stays alive and records a pending cut in its Status parent.
After the current frame's DrawSync returns at `0x8001d5a0`, the hook resolves the
parent through the engine's current mode owner and revalidates the selection,
feature, visitation, source and story. The same policy resolves departure and
arrival on selection and at commit, including completion flags that may change
without the story word changing. It clears only the two verified 320×240
display rectangles with GPU fill commands before the loader reuses menu resources.
An unfamiliar display layout aborts
the request. The cut is immediate; it does not add a timed fade.

The hook then changes the field-return stage and coordinates at `0x80048d68`
and writes the same mode queue as the resident request function `0x80016b88`.
The mode owner `0x80020b58` recursively destroys its children before the next
overlay loads, including the still-open Status/map tree. No intermediate root
menu is constructed. A consumed or rejected request is cleared. A rejected cut
leaves the map open. Party, inventory, quest and visitation flags are not written.

Older savestates made during the previous root-menu closure retain their original
completion path: page 5 and a mapped cancel finish the native close animation,
with the same policy revalidation at `0x80013318`. Disabled or stale legacy requests
return to the original field. New and old requests store their complete state in guest
RAM so restoration does not depend on host pointers or timers.

The native map-name panel retains the original name and adds a second line with
the available action or reason. Its text hook uses the normal encoded text setter;
the original artwork and cursor remain in use.

## Validation and remaining coverage

The native regression checks controller allocation, exact visitation, free-cursor
rejection, unknown overlays, unsupported sources/servers/story states, input
priority, deferred commit, repeated callbacks, pending-state restoration,
disabling the feature before commit, competing transitions, display-buffer bounds,
name preservation and allowed write locations.
Story tests cover Seiryu before/after the announcement, recovery travel into the
city, Asuka's incomplete/completed encounter, lockdown phase boundaries, full-word
story validation, and subflag changes during both current and legacy requests.
South tests cover both directions before/after the arrival scene, missing station
and landing visits, Bulk Swamp's shared icon, and visit changes while a current
or legacy request is queued. Unvalidated neighboring fields remain excluded.
The build runs six Shinka native suites. Python tests verify data generation and
revision rejection, as well as existing configuration and patch tooling.

Initial live testing verified the first six arrival points and movement after arrival, including
a continuous route through Central Park, Wire Forest Entrance, Wire Forest,
Asuka's bridge and Pelche Oasis, plus a separate Seiryu City trip. The checked
story flags remain unchanged across the route. A state saved during menu closure
completes its pending trip after a full process restart. Two-area map names fit
on one line, leaving the second line for the travel hint.
Unsupported selections and ordinary cancellation retain the original location.
Legacy map states show the reopen instruction and close normally. The portable
lab's return guard accepts both controller allocations; its regression test covers
both layouts with and without Card Folders.

Testing uses a copied save profile. Destination screenshots, state files,
route records and save-specific details remain local and are not published.
Initial code checks and travel routes do not establish full campaign safety.

The direct-cut build additionally verifies a trip and return trip, movement after
arrival, destruction of the old menu tree, absence of an intermediate root,
ordinary cancellation, unsupported selections and legacy pending travel states.
A new state saved during area loading also completes after a full process restart.

Story-guard testing additionally uses controlled early-event fixtures in a copied
advanced profile. Seiryu blocks travel before Teddy's announcement; the original
conversation sets its completion flag, and returning on foot immediately restores
travel while the main story value stays unchanged. Asuka's alternate arrival
starts Keith's dialogue and battle. Winning and finishing the dialogue sets his
completion flag normally. A savestate reload retains it, and a trip to Central
Park and back uses the usual bridge coordinates without repeating the encounter.
An unedited story-20 copied checkpoint also lands outside Asuka's closed gate;
walking to it and confirming leaves the player outside. Both the released Seiryu
trip and the lockdown arrival leave the checked progression bytes unchanged.
The fixtures validate these predicates and transitions, not every prerequisite
in a naturally played campaign. Full lockdown/reopening coverage remains pending.

The South expansion was checked with another isolated copied profile. A map trip
through all three first-arrival landings retained the checked progression bytes. The station
console returned to East Station normally. Tranquil Swamp's boardwalks lead to its
entrance island and the original Bulk Bridge transition; that transition was
crossed in both directions. Walking from the Bulk Bridge teleport landing also
reached the Tranquil Swamp exit. A battle/reward sequence returned to the field
during these checks; later walking probes used an extended encounter countdown in
the disposable state to isolate movement.

A controlled arrival fixture reset the main story to `6` in a copied later save
and used the station controls to enter South Station. Its original scene advanced
to `7` and moved the party to Bulk Swamp. This tests the arrival release condition;
it does not replay the Blue Card errands or certify the first Bulbmon battle.
The final build restores a map savestate in Bulk Swamp, travels to Tranquil Swamp,
and returns to Central Park. Pending-story and missing-station fixtures reject
travel, with their instructions fitting the native map panel. Private captures,
states and fixture details remain excluded from Git.

Phoenix Bay was subsequently loaded using developer warps from Central Park at its native south-side
bridge coordinates and returned to Central Park with exact stage and position
checks; reloading the copied savestate preserved the Phoenix landing. The native
Jungle Grave entry was also exercised from a story-7 fixture: its Zanbamon scene
returned the party to Bulk Bridge and advanced the story to 8. Jungle Grave remains
excluded so that event-owned return stays under the original field script.

The chapter-25 Phoenix Bay earthquake now has a conditional arrival: while
native flag `0x1c51` is clear, travel lands at the northern approach so the
original event can run. The regular landing missed this trigger in a controlled
fixture. Once the game completes the event, travel returns to the south bridge.
The player-map path was checked with directional input and Cross in an isolated
fixture, and the native dialogue completion set the flag without a debug write.
See the [event predicate and validation limits](travel-story-audit.md#phoenix-bay-earthquake-and-jungle-grave-follow-up).

## Reference and next work

Flawe's Fast Travel 2.0, inspected in the pinned
[D-W-3-Recomp reference repository](https://github.com/Xive080/D-W-3-Recomp), supplied
useful leads for the map task, field-return context, arrival coordinates and
plot-dependent entrances. Its replacement game module was not installed or
distributed with Shinka. This implementation uses native hooks, its own pending
state and a narrower destination policy.

The reference documents inaccessible post-game destinations with missing NPCs
and underwater/underground crashes. Expanding this network therefore requires
validated arrival points and current story/server access, rather than simply
enabling every previously visited icon. Next work includes more surface locations,
safe dungeon exits, later campaign transitions and post-game boundaries.

The [walkthrough and story-gate audit](travel-story-audit.md) scopes the campaign
checkpoints, reference-code predicates and before/after tests needed for that
expansion. The Seiryu departure and early Asuka approach rules are implemented;
the other proposed restrictions remain investigation work.
