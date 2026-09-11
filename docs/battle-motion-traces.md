# Battle motion trace reports

`tools/analyze_battle_motion.py` turns a bounded write trace into an ordered
timeline of clip requests, selections, loops, completion signals, and camera
sets. It runs offline and does not change game speed or enable a runtime recorder.
See [the animation investigation](battle-animation-speed.md) for the supported
field layout and the remaining runtime work.

```powershell
python tools/analyze_battle_motion.py `
  --trace output/battle-motion/technique-trace.json `
  --ram output/battle-motion/technique-before.bin `
  --output output/battle-motion/technique-report.json
```

Use the raw 2 MiB snapshot taken before arming the trace, from the same copied-save
battle session. Output must be a new path. Reports contain the SHA-256 of both
inputs; these hashes do not establish which executable produced them. Keep RAM,
traces, and derived reports under ignored `output/`.

## Capture contract

Input JSON contains `models` and corresponding `controls` address arrays,
`spans` as `[lo, hi)` watched ranges, and `trace` as the ordered entries from the
debug server's targeted `wtrace_dump`. Addresses may be integers or `0x` strings.
Each entry needs `seq`, `frame`, `addr`, `old`, `new`, `pc`, `ra`, and `w` (width
in bytes). Physical RAM, KSEG0, and KSEG1 aliases are normalized.

For each model, watch `+0x78..+0xa4`; for its control, watch `+0x00..+0x28`.
Optionally watch camera-controller `+0x50..+0x108` and the shared step word
`0x800a4464..0x800a4468`. Resolve object addresses from the
[runtime object map](runtime-objects.md), not from another checkpoint's addresses.

Reset the targeted recorder immediately before the bounded action, then disarm
it before retrieving pages. Record its unfiltered `total` and `available` counts
in `recorder: {"total": N, "available": N}`. Both must equal the number of saved
entries. Retrieve every entry in order; narrow frame windows when a page hits
the server's 2,048-entry limit. Do not sort, renumber, or discard unchanged writes.

The analyzer rejects sequence gaps, duplicate/out-of-order entries, decreasing
guest frames, inconsistent overlapping old/new byte values, missing watch
coverage, and mismatched recorder totals. Legacy captures without `recorder`
remain readable, but explicitly report `recorder_totals_verified: false`:
consecutive sequences cannot prove that a tail was not omitted. This is an
integrity check of the supplied evidence, not an independent audit of its producer.

## Reading the report

Only models below a reachable combatant group are accepted. A scenery model
sharing the model callback is rejected. Snapshot control pointers must match the
capture's pairs. These checks establish initial ownership; they cannot prove
that an allocation remained the same object throughout the trace. Inspect the
raw evidence if a battle changes mode, creates/replaces actors, or uses another
overlay revision. Partial writes to decoded model/control words are rejected
until a decoder supports them; mixed-width camera payload writes are checked
for byte continuity without guessing their meaning.

Each actor has a compact `clip_sequence` and individual `segments`. Selecting
the same clip again starts a new segment even though the compact sequence does
not change. Initial segments are marked as already underway; final segments
end with `capture_end`, not an inferred completion. When available, the first
clip store's old value seeds the starting clip because the snapshot precedes
recorder arming. Otherwise the report labels the snapshot-derived seed.

`advance_histogram` counts timeline entries advanced per update. Those entries
are distinct from guest frames. Loop events are recognized by the verified loop
store, not by treating every backwards position write as a loop. Completion and
notification are separate events, as are requests and actual clip selections.
The combined `events` list retains sequence order when several events share a
guest frame. Camera direct sets count even when their progress word stays at
4096; these are not interpolation updates.

## Script lifetimes, commands, and waits

Optionally add `scripts`, an array of allocation addresses to investigate, and
watch each entire `address..address+0xb4` range. These addresses are **leads**, not
assumed script objects. In the live fixture, one allocation successively held a
menu controller, a transition controller, an attack script, and another
transition controller. Air Blast allocated its defender script somewhere else
than the basic attack did.

The decoder follows callback stores at `+0x48`. Only periods tagged with script
callback `0x8008c590` are decoded. A replacement closes the lifetime; a subsequent
activation starts a new epoch. It retains counts of ignored writes from other
owners. The initial callback seed uses the first callback store's old value when
available, otherwise the snapshot, and labels which it used. As with model
inspection, callback recognition is not a general memory-allocation oracle.

Store-site-specific register evidence is required for parsed command operands.
The outer command-fetch store verifies that `s1` matches the watched controller.
Script cursors are halfword aligned, unlike the word-aligned controller headers.
Consecutive fetches at the same cursor/opcode are grouped as attempts, with
first/last frames; they are not claimed to be unique command executions.

The combined event list distinguishes:

- Clip-completion waits from other actor-command waits at the shared rewind site.
- Effect/resource polling from the explicit script delay counter.
- Delay starts and elapsed signals, including signed countdown overshoot.
- Effect commands and sound commands, with their original selectors/operands.

These are parsed requests. For example, sound selectors 98/99 can be resolved
from actor results later in the handler. The report does not silently substitute
an assumed sound ID, count each poll as another sound, or claim audible playback.
Likewise, an effect-resource wait is not evidence that every visible effect frame
has been mapped.

## Damage preparation and battle-local HP/MP

Watching `0x800a43f4..0x800a4530` adds the shared damage result and six battle-local
stat records. The result word at `0x800a441c` has distinct observed basic/technique
preparation stores. The table starts at `0x800a4470`, stride `0x20`; current HP
is halfword `+0x08`, current MP is `+0x0c`. Maxima are `+0x06` and `+0x0a`.
Only fully watched records are described. These slots are not the eight saved
rookie records; snapshot values are labeled separately from traced changes.

Basic and technique HP subtraction/clamp stores have separate event kinds.
Negative intermediate HP is reported with `new_signed` as well as the raw
halfword: a lethal subtraction followed by a zero clamp is not a heal or a second
hit. Other writers remain visible as unclassified HP/MP writes. Unsupported
write widths overlapping decoded fields fail instead of silently dropping an
update. Damage-result preparation is separate from the later HP update, and
neither alone timestamps the visible hit.

These reports establish a normal-speed baseline. They do not predict accelerated
battle duration, certify visual/audio synchronization, or replace a comparison
of completed-battle party records. An accelerated build still needs fresh
captures and outcome checks.
