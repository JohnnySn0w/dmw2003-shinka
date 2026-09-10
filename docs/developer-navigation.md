# Developer navigation and test fixtures

## Offline field-condition inspection

`tools/field_conditions.py` reads known 24-byte field condition/action records
directly from an extracted original module. For example, with your local module
path substituted:

```powershell
python tools/field_conditions.py WSTAG500.PRO --offset 0x1c60 --count 2
```

The JSON includes the input SHA-256, both condition pairs, readable story
comparisons or supported bit addresses, and action-8 event IDs. Class-0x60 story
conditions use equality for a nonzero value and inequality for zero. Class-0x1c
and class-0x40 bit storage are decoded separately. Unknown classes remain
unresolved, and the trailing type-dependent words are not interpreted.

This is read-only and does not need a running game. It accepts explicit offsets
from traced tables; it does not scan for plausible records or establish that a
record is reachable. It also does not decode scene bytecode, trigger geometry,
or event completion. Verified examples: WSTAG485 offset `0x172c`, WSTAG480
offset `0x23b8`, and the two WSTAG500 records above. Unit tests use synthetic
bytes rather than redistributed game data.

## Live navigation

`tools/field_triggers.py SNAPSHOT.ram` decodes the original field's layer-7
trigger map from a complete 2 MiB RAM snapshot. It resolves the loaded resource
through the resident resource table and follows the native 128/64/32/16/8-pixel
compressed lookup. It reports each nonzero trigger byte, its index and input bank, sampled
bounds and an actual point with that trigger value. Multiply map pixel
coordinates by 256 for a field-return coordinate fixture.

The default sample stride is 4; `--step 1` checks every pixel. Bounds can merge
disconnected regions and are not walkable polygons; use the reported sample or
query `TriggerMap.at(x, y)` for a specific point. Smaller regions may be missed
at coarser strides. Trigger indices select 24-byte records in the field's action
table; they are not event IDs. Story conditions still decide whether an event
runs. Index zero is valid with nonzero bank bits; only byte zero is empty.
Unsupported overlays, unloaded resources, invalid pointers and out-of-map
queries are rejected. Synthetic tests compare every pixel of a two-block map
against independently populated data and cover all compression levels.

This is an offline, read-only investigation tool. A RAM dump and the decoded
map remain local in ignored output; no game resources are included in Git.

`tools/dev_nav.py` controls the local runtime built with `PSX_DEBUG_TOOLS=ON`.
It provides named warps, position bookmarks, frame-counted input, route scripts,
screenshots, savestate checkpoints and explicit progression/combat edits.
These are investigation tools; the player map continues to enforce its own
visited-area and story rules.

Use a copied [save profile](save-profiles.md) for fixtures. A warp can enter an
unvisited area, whose original scripts may then set flags. A story-number edit
does not reconstruct completed quests, inventory, boss results or server access.
Use a progressed checkpoint when testing a coherent campaign state.

## Commands

Launch with a dedicated profile and debug port (the launch script defaults to
4380). From the repository root:

```powershell
python tools/dev_nav.py where
python tools/dev_nav.py lab
python tools/dev_nav.py save 8
python tools/dev_nav.py points
python tools/dev_nav.py warp central-park
python tools/dev_nav.py encounters defer
python tools/dev_nav.py press ne 12 --measure
python tools/dev_nav.py mark park-path
python tools/dev_nav.py warp park-path
python tools/dev_nav.py shot output/nav-park.png
python tools/dev_nav.py load 8
```

`save` overwrites that slot in the running profile. `load` restores it. Port
selection precedes the command: `python tools/dev_nav.py --port 4381 where`.

`lab` is a read-only, single-command snapshot of the physical or portable lab:
root lifecycle/phase, selected party slot, rookie indices in the three slots,
and action-menu phase/row. It rejects other overlays and invalid owner chains.
An absent action menu is reported as address zero; its phase/row are then unused.
This separates partner selection from action selection without injecting input.

`where` is read-only and reports the **cached field-return position**, which can
lag behind walking. `where --refresh` briefly opens and closes the field quick
menu so the native game samples the current coordinates. `mark` and directional
`press --measure` use that refresh. If a quick menu is already open, it is left
open. Refresh stops if a battle or another mode interrupts it.

Button durations use emulated input frames and a neutral release interval,
including under turbo. Directions are screen/controller directions; projected
world coordinates are not a simple north/east grid. `--measure` reports actual
coordinate deltas for that step; collisions and path bends limit extrapolation.
Cross is explicit (`press cross 4`): automatic confirmation near water can start
fishing instead of taking an exit.

Twelve built-in points include the eleven player travel destinations plus the outer
Asuka bridge approach. Named bookmarks default to ignored
`output/dev-nav-points.json`; `--bookmarks PATH` selects another file. Bookmarks
store only stage, position and facing. They never restore a captured story value.
Built-in point names cannot be overwritten. For new-area investigation,
`warp-raw STAGE X Y FACING` accepts decimal or `0x` hexadecimal values. A valid
numeric field ID does not establish a tested, walkable landing.

Warping opens the native map when necessary, queues the destination, then
samples the actual arrival position. A mismatch stops with an error instead of
reporting the cached request as a successful landing. A scene that moves the
player on arrival can therefore require a different checkpoint or landing.

## Progression and combat fixtures

For native entry tests, `python tools/dev_nav.py enter 0x23e` queues the original
field-to-field loader from Phoenix Bay into Suzaku. `enter 0x23b` is supported
from Suzaku in the reverse direction. These are the only admitted connections,
traced from WSTAG485 offset `0x162c` and WSTAG500 offset `0x1bf0`.
The command requires the current field and mode owner to remain valid, rejects
an already queued transition, and writes the complete queue word atomically.

Unlike `warp`, `enter` leaves the field-return coordinates alone and lets the
native loader choose its entrance. It returns a queue-time snapshot, **not an
arrival or scene-completion assertion**. Inspect `where` and a screenshot after
loading; the cached return position can still describe the old field until a
normal menu refresh. These developer transitions bypass walking to and using
the exit and do not certify the exit's trigger conditions or quest sequence.
Use a copied fixture profile. Player-map travel permissions are unchanged.

```powershell
python tools/dev_nav.py save 8
python tools/dev_nav.py story 6
python tools/dev_nav.py flag 0x4011 0
python tools/dev_nav.py party
python tools/dev_nav.py heal 2
python tools/dev_nav.py power 2 999
python tools/dev_nav.py encounters next
python tools/dev_nav.py load 8
```

`heal INDEX` restores that rookie record's current HP/MP to its existing maximum.
`power INDEX VALUE` sets base strength within the native 1..999 limit. `party`
reports all eight rookie records and their numeric indices, including inactive
records: 0 Kotemon, 1 Kumamon, 2 Monmon, 3 Agumon, 4 Veemon, 5 Guilmon,
6 Renamon, 7 Patamon. These edits are made in the field before battle; live battle actors
may hold separate copies. They are one-time edits, not an invulnerability toggle,
and can be saved by the game. Load a checkpoint to undo them. Neither command
changes EXP, equipment, maximum HP/MP, defense or evolution ownership.

`encounters defer` extends the current field's random-encounter countdown.
`encounters next` reduces it to zero for the next eligible random check. Both
preserve the native encounter enable flag and Shinka's countdown-unit marker.
Normal loading/reset logic can replace the countdown; scripted encounters and
the player's encounter-rate setting still apply.

Story writes accept 0..255. Flag writes are restricted to the four class-0x40
flags traced during the current travel audit: 0x4006, 0x4011, 0x4016 and 0x4018,
plus Phoenix Bay's class-0x1c flag 0x1c51. The latter uses its own native storage
base. Clear it only in an isolated fixture to investigate the pending event;
observe the native completion callback setting it during a successful replay.
See [story evidence and limitations](travel-story-audit.md). No command claims
to jump to a fully reconstructed plot chapter.

## Routes

A local JSON file records each button step with its required starting and ending
mode. For example, these are two small movements within Central Park:

```json
{
  "schema": 1,
  "steps": [
    {"before": "0x21d", "button": "ne", "frames": 6, "after": "0x21d"},
    {"before": "0x21d", "button": "sw", "frames": 6, "after": "0x21d"}
  ]
}
```

Run `python tools/dev_nav.py route output/route.json`. The whole recipe validates
before input. Each step checks its starting mode and waits for its expected
ending mode; an unexpected battle stops further route steps. A running button
step can last up to 300 frames before that ending check. Routes return a JSON
record of their before/after states. They do not establish collision-free paths
without live testing, and an in-area dialogue may share the field's mode ID.

## Implementation evidence

The `shinka_nav` command is inserted into a generated copy of the pinned
framework's debug server. The dependency checkout remains untouched. Handlers
execute at the emulation thread's debug polling point. Unlike the existing
byte-only `write_ram` command, a warp writes all four return-context words and
the transition parameter, then queues the complete destination mode last. The
native mode owner performs recursive teardown and normal area loading.

Mutations reject a changed source mode, an already queued transition, or an
unready mode owner. Coordinate warps require Status mode; the CLI opens the map
first. A direct field-to-field queue uses native entrance coordinates instead
and is rejected. The other edits require
a field mode. These checks reject the wrong load state, but do not imply that
every event within an otherwise valid field is safe to skip.

Verified against the supported local executable:

- Field-return context: `0x80048d68`; mode/queue: `0x8004b3f8/0x8004b3fc`.
  Resident queue implementation: `0x80016b88`.
- Rookie records: `0x8004949c`, stride `0x3dc`, confirmed by resident accessor
  `0x80017b4c`. The combat edit validates its base/stride signature in RAM.
- Current/max HP: `+0x20/+0x22`; current/max MP: `+0x24/+0x26`.
  Native refill at `0x80011098..0x800110a8` copies those exact maxima to currents;
  the event refill at `0x800159cc..0x800159d8` does the same from the save base.
- Base strength: `+0x28`. Native stat mutation at `0x800170c8` clamps HP/MP to
  9999 and the strength/stat group to 999. This tool does not increase maxima.

The existing retail memory-card/profile files remain independent of the CLI's
ignored route and bookmark files. Native tests cover rejected operations, queue
write order, stat bounds and preservation of adjacent fields. Python tests cover
failed responses, bookmark isolation, atomic warp requests and route stopping.

## Live validation (2026-09-09)

Tested with a copy of the South Sector test profile and the retail BIOS backend:

- Exact stage, X/Y and facing read back after Central Park, Bulk Bridge,
  Tranquil Swamp, South Station and a custom Central Park bookmark arrival.
- A 12-frame northeast step measured X +10416, Y -5208. A two-step six-frame
  NE/SW route returned to its starting X/Y. Menu sampling waits for input phase
  3 so a close press cannot disappear during the opening animation.
- A depleted Patamon fixture (12/962 HP, 7/1231 MP) refilled to its existing
  maxima; the complete rookie record matched the original healthy record.
  Strength 104 -> 999 preserved every other byte of that record. Patamon then
  completed a normal Tapirmon battle; this was not a comparative damage test.
- An attempted refill inside battle was rejected. Story and quest-flag edits
  changed the intended data, and loading the checkpoint restored story, flags
  and all eight reported stat records. Loading also restored strength to 104.
- The copied first memory card retained the source card's SHA-256. All fixture
  saves, route logs and screenshots stayed in ignored local output.

Final Windows build succeeded; seven native regression suites and 40 Python
tests passed. No always-on combat patch or general chapter-skip recipe is claimed.
