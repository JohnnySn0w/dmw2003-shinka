# Map travel

The experimental English expanded menu supports **X to travel** from the original
map. Move the cursor until it snaps to an icon. Eligible locations show
**X: Travel** beneath their original name. Confirm closes the map and Status menu,
then uses the original field loader to arrive. Triangle without confirming closes
the map normally.

The initial travel network connects these Asuka locations:

| Map icon | Arrival |
| --- | --- |
| Asuka City | Bridge, outside the plot-dependent Main Lobby entrance |
| Central Park | Paved plaza |
| Wire Forest Entrance | Open path |
| Wire Forest | Clearing near the path |
| Seiryu City | Outdoor city path |
| Pelche Oasis | Path near the waterfront |

The exact arrival area must already be visited in the loaded game. One icon can
represent several rooms, so having the icon visible is insufficient. A location
you are already standing in shows that status instead of offering travel.

Travel currently starts from these same outdoor fields, plus Asuka Main Lobby.
Other interiors, dungeons, other servers and unvalidated late campaign states
show an unavailable message. There is no cross-server map switch. The build
accepts story byte values 1–36 for this initial network; this is a conservative
validation boundary, not a claim that every later value denotes post-game.
Broader campaign coverage, additional arrival points and post-game routes remain
work to do. Existing map navigation and visibility rules are preserved.

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
boundary, lifecycle and complete guarded code/data ranges.

`src/map_travel.c` extends the Status controller body from 0x78 to 0x88 bytes,
storing a pending marker, icon, source and story snapshot. Its child array gains
one null slot; the resulting child count identifies the new allocation without
reading past old savestate allocations. The existing destructor owns every child.
All pending travel state is serialized in game RAM. Host-side memory stores only
temporary text that the original text setter copies into its own allocation.

On confirm, the map follows its normal teardown. The Status controller marks its
new root with page 5 and its parent pointer; a mapped cancel input then drives the
original full-menu close animation. At the resident transition's return address
`0x80013318`, the hook revalidates the pending selection, feature, visitation,
source and story. Only then does it change the field-return stage and coordinates
at `0x80048d68` and the transition argument. A consumed request is cleared.
Disabled or stale requests return to the original field. Party, inventory,
quest flags and destination visitation flags are not written by the hook.

The native map-name panel retains the original name and adds a second line with
the available action or reason. Its text hook uses the normal encoded text setter;
the original artwork and cursor remain in use.

## Validation and remaining coverage

The native regression checks controller allocation, exact visitation, free-cursor
rejection, unknown overlays, unsupported sources/servers/story states, input
priority, deferred commit, repeated callbacks, pending-state restoration,
disabling the feature before commit, name preservation and allowed write locations.
The build runs six Shinka native suites. Python tests verify data generation and
revision rejection, as well as existing configuration and patch tooling.

Live testing verifies all six arrival points and movement after arrival, including
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
