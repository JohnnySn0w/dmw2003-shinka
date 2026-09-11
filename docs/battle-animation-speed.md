# Battle animation speed investigation

Status: default-off 2x model-timeline prototype, 2026-09-11. The two separate
menu controls are still pending. Work resumed after the user's CPU-heavy task cleared; the
[battle geometry optimization](performance.md) reduces execution cost without
changing animation speed. Its rendering routines are not yet an identified
model-animation clock.

## Controlled prototype

`SHINKA_BATTLE_MOTION=2` enables the diagnostic prototype for the process. An
unset variable or any other value keeps original motion. It is not a saved
preference and is not exposed in Settings yet. The playable installation remains
unchanged while the prototype is evaluated in a separate build against copied
saves.

The owned interpreter copy intercepts only the cycle-aware load of `0x800a4464`
at `0x80083d30`. It preserves that load's timing/hazard accounting and subsequent
PGXP processing, then substitutes the model-local step. It never writes the
shared delta, advances the battle script itself, or changes camera interpolation,
audio rate, input, or host pacing. This does **not** guarantee identical camera
cue timing: finishing a pose can release a script wait earlier.

The hook checks the active battle mode, follows the live owner/wrapper/battle/
combatant-group graph, verifies controller signatures and the model's group
membership/action record, and compares the live setup/timeline/update code with
guards generated from the supported owned `FIGHTSTG.PRO`. It rejects ambiguous
ownership, unsupported overlays, out-of-bounds tables, completed clips, and
unexpected elapsed steps. Scenery sharing the model callback is excluded.

The experimental rate doubles steps 1–4 and stops at the first loop/end marker
or final entry, leaving marker processing and completion notification to the
original routine. Remainders are discarded at boundaries; there is no host-side
phase state to leak across save loads or allocation reuse. Ordinary interpolation
entries with the high bit set are not mistaken for exact `0x8000` loop markers.

Scope remains deliberately experimental: all eligible combatant clips receive
the same rate, including reactions and casting loops. The prototype does not yet
classify attack versus ordinary motion or validate digivolution, multi-hit,
counterattack, boss, or multi-enemy sequences. A native overlay that bypasses the
interpreter site will retain original speed; the currently generated battle
geometry overlay does not contain this timeline routine.

Native regression tests cover marker crossings, clamping, invalid ownership and
pointers, changed overlay bytes, immediate recovery after rejection, and absence
of guest-memory writes. Local generated guard bytes and game captures remain
ignored and are not distributed.

### Graphical prototype validation

The earlier AMD OpenGL startup stall did not recur in this session. Both rates
ran through the graphical runner using the same copied slot-10 checkpoint.
The default build and 2x basic-attack replay both returned to the field with all
7,904 saved party bytes equal to the existing reference. Air Blast also returned
to the field at both rates with identical saved party bytes and the expected
24 MP cost. Rendered damage screenshots were inspected separately from the trace
analysis; the immediate field screenshot caught the loading transition and is
not evidence of a fully rendered field. This is not an audio/pitch or visual-taste
acceptance test.

| Patamon segment | Original step | 2x model step |
| --- | ---: | ---: |
| Basic clip 15 | 18 frames | 8 frames |
| Basic clip 16, script-held | 52 frames | 52 frames |
| Basic clip 17 | 18 frames | 8 frames |
| Basic clip 18, script-held | 112 frames | 114 frames |
| Basic clip 19 | 26 frames | 14 frames |
| Air Blast clip 39 | 207 frames / 3 loops | 207 frames / 9 loops |

These are captured guest-frame spans between clip selections, not exact
wall-clock benchmarks or a promise of a 2x faster turn. The complete clip
sequences, completion notifications, parsed sound/effect command sequences, and
explicit script-delay operands were preserved in the paired captures. Camera
updates continued through their original direct-set path; this checkpoint does
not exercise the camera interpolation path. Cue times may move with script waits.

The basic attack prepared 815 damage at both rates. Air Blast prepared 969 in
the fresh 1x trace and 976 in the 2x trace (an earlier headless recording prepared
440). Repeating the 1x trace again produced 969 and the same 10,462 write count.
Preparation occurred 198 frames after trace start in both 1x runs, versus 195
frames at 2x. This timing difference precedes the selected attack clip and needs
an RNG/control-flow trace; it has not been established as harmless variation or
a damage-calculation regression. Both defeated the same 120-HP enemy. Matching
post-battle party bytes therefore cannot establish identical damage rolls or
nonlethal battle behavior. Do not claim general battle-outcome parity from this
checkpoint. Resolve this before adding player-facing rate controls.

Local evidence: `output/battle-events/motion-{default,double}-{basic,air}-*`,
`output/motion-prototype/comparison.json`, and the matching outcome/screenshot
files. Diagnostic executable SHA-256:
`d45d300349019cbdc7953f06b853bf8077ea7476b4de22049bb7c95c58cb3dc7`.
Validation: 134 Python tests, 13 native tests, and Ruff passed.

## Intended controls

Add two independent rows to the existing in-game Settings menu:

| Setting | Intended scope | Initial choices |
| --- | --- | --- |
| Battle model motion | Idle poses and ordinary model motion outside attacks | 1x, 1.25x, 1.5x, 2x |
| Attack animation | Attack motions; include related hit/recovery motion only where needed for synchronization | 1x, 1.25x, 1.5x, 2x |

Both default to 1x. The attack rate replaces the ordinary motion rate during an
attack; the two settings do not multiply. Preserve camera speed, soundtrack and
sound pitch, menu input, and battle outcomes. These ranges and motion categories
are a proposed starting point, pending verification of the game's actual clocks.

Changing pose playback alone may make a swing finish earlier without shortening
the turn: the camera or an event script could still be waiting. Determine that
behavior before promising shorter battles. Spell effects and digivolution
sequences need their own checks and should not inherit an unverified speed hook.

## Initial static leads (resolved below)

Inspection uses the pinned local ddw3 disassembly as a reference, without copying
its implementation. `FIGHTSTG.PRO` is mapped at `0x80082cb0`. `WFIGHTMN.PRO` and
`WFIGHTTS.PRO` are additional candidates for the battle update investigation;
offset-only listings need their runtime mapping established before using them
as hook addresses.

The battle stage makes indirect service calls, as well as resident graphics and
object calls. The following are probe leads, **not identified animation hooks**:

- Around `0x8008ad10`–`0x8008ae94`, a path interpolates three-component values,
  calls resident transform functions, and invokes a service callback at offset
  `0x164` after lookup through `0x8004df8c`. Trace this to distinguish camera,
  model, and other transform ownership; leave it untouched until classified.
- Around `0x80091b8c`–`0x80091c08`, another path invokes a service callback at
  offset `0x15c` for service ID `0x1009`, then decrements a field at object offset
  `0xe4`. A decrementing field alone does not establish an animation clock.
- The pinned runtime's `mod_builtin_speed.c` covers loading/CD acceleration;
  it does not supply a verified per-model battle animation control.

Do not accelerate VBlank, host pacing, or the complete battle update to implement
these settings. Those approaches can also change camera motion, input timing,
sound, or gameplay. The existing widescreen/zoom projection hook does not
identify animation timing either.

## Live model timeline audit — 2026-09-11

The [object-map tool](runtime-objects.md) distinguishes controller candidates
from objects reachable through the mode owner's child graph. The copied battle
checkpoint yielded these addresses; they are not stable hook constants:

| Role / evidence | Controller | Update callback |
| --- | --- | --- |
| Combatant group, two occupied model slots | `0x800dfccc` | `0x80087bb0` |
| Patamon model, 11 child slots | `0x8010e440` | `0x80083e0c` |
| Kunemon model, 15 child slots | `0x8012e5a4` | `0x80083e0c` |
| Separate environment model, 14 child slots | `0x800dff9c` | `0x80083e0c` |
| Lighting controller | `0x800dfe74` | `0x8008aaf0` |
| Separate transform-controller candidate | `0x80135a84` | `0x80091cf4` |

The earlier `0x8008ad10` lead belongs to lighting: it interpolates three light
descriptors and background color, then saves lighting state through callback
`+0x164`. Live service lookup `0x8004df8c` resolves to `0x8001da84`; the 30-slot
table has pointers at `0x8004de70` and IDs at `0x8004dee8`. Observed services use
`0x8001e4f4` at `+0x164`, which copies the lighting matrix buffer.

Service `0x1009` was `0x8013590c`; its `+0x15c` callback resolved to `0x8001e404`,
which enables/stores a buffered transform. The earlier `+0xe4` countdown in
`0x80091cf4` is armed with two refreshes. Neither is the combatant's clip clock.
The camera audit below separates interpolated trajectories from direct sets.

### Verified stores and timeline structure

The model update calls `0x80083c30`, then evaluates poses through `0x80083854`.
Targeted write traces directly observed these model-relative fields:

| Offset | Observed role | Store / behavior |
| --- | --- | --- |
| `+0x64` | Pointer to requested-action/control data | Patamon `0x800dfd1c`, Kunemon `0x800dfd68` in this checkpoint |
| `+0x78` | Selected clip ID | `0x80083a94`; setup resets progress/completion |
| `+0x7c` | Completion latch | Set at `0x80083d90`, cleared at `0x80083a9c` |
| `+0x80` | Expanded timeline position | Advanced at `0x80083d3c`, clamped at `0x80083d4c`, loop target stored at `0x80083d88` |
| `+0x84` | Pose/frame selection | Written at `0x80083d24` or `0x80083cfc` |
| `+0xa0` | Expanded timeline entry count | Set by clip setup at `0x80083c10` |

Control-block `+0x08` requests a clip; `+0x10` receives completion at
`0x80083d98`. In the basic attack, the action controller consumed completion,
requested the next clip at `0x8008b8f0`, and cleared completion at `0x8008b92c`.
Early completion therefore changes action sequencing, not just a drawn pose.

The timeline uses entries at `+0xa4`, companion values at `+0xd24`, and
interpolation/source data at `+0x19a4`. Static inspection identifies `0x8000`
as a loop marker and `0xffff` as completion at the selected next entry. Setup
expands interpolation spans in advance. These are not plain consecutive model
frames; a rate change must account for marker crossings and clip replacement.

Progress increments come from shared word `0x800a4464`, written at `0x8009e47c`.
Recorded increments included 1–4 entries per model update. Other battle routines
read this word. Do not treat it as a constant one, multiply the global value,
or assume one model update equals one guest VBlank.

### Basic attack versus Air Blast

Frame-counted inputs from copied slot 10 produced two bounded write traces.
Recording covered model/control fields, the shared step, and separate transform
ranges. The ring was disarmed before retrieval; eight-frame pages recovered every
entry, with totals checked against ring availability:

- Basic attack: 10,032 writes across guest frames 19,672–20,493. Patamon selected
  `1 → 15 → 16 → 17 → 18 → 19 → 1`; several clip ends latched completion and
  handed control back to the action sequencer.
- Air Blast, selected from the visible technique menu: 13,826 writes across
  frames 36,667–37,776. Patamon selected `1 → 39 → 1`. During clip 39, its
  timeline looped from 140 to 100 three times, then an external request replaced
  the clip without setting its completion latch. Kunemon followed
  `1 → 5 → 6 → 7 → 11` in both traces. IDs describe this resource/checkpoint;
  they are not a universal action classification.

Changing the casting pose's speed alone may leave the effect/action duration
unchanged. Hit, sound, effect, camera-wait and resource-update boundaries are
not yet fully audited; no accelerated outcome is claimed. The function-entry
probe missed some controller paths despite their verified stores. An empty
function-entry sample is not proof of inactivity.

Local captures, graphs and traces are under ignored `output/battle-motion/`.
A normal-speed reference replay after tracing matched all 7,904 party-record
bytes and returned to the field. The diagnostic process was stopped. No runtime
patch was needed for this audit.

## Camera and action-script boundaries — 2026-09-11

The new [motion trace analyzer](battle-motion-traces.md) reproduces both captured
clip sequences, validates every supplied sequence number and overlapping byte
history, and separates loop, request, selection and completion events. The older
captures checked recorder availability during collection but did not retain those
counts in JSON; their reports therefore leave recorder-total verification false.
Future captures should retain those counts alongside the entries.

The reachable controller `0x800daa30`, callback `0x80091df4`, targets service
`0x1001` in this checkpoint. Its update builds a view transform through resident
`0x8002a1ac` and submits it through service callback `+0x15c`. The interpolation
path reads the elapsed-step provider at `0x8004df9c`, advances `+0xf0` toward
4096 at `0x80091ee0`, and interpolates its source/target vectors. This is separate
from the model's timeline-position store. It is not evidence that every battle
camera trajectory uses this interpolation path.

In fact, the supplied traces recorded **zero** updates at `0x80091ee0`. All
observed camera progress writes came from the direct setter `0x80092244`, whose
store at `0x80092290` sets progress to 4096:

| Capture | Direct sets | Return addresses at the setter |
| --- | ---: | --- |
| Basic attack | 40 | `0x80087adc`: 39; `0x80087b70`: 1 |
| Air Blast | 69 | `0x80087adc`: 66; `0x80087b70`: 1; `0x8008c204`: 2 |

The action-script camera handler at `0x8008c004` dispatches through the camera
controller's direct-set or interpolated-set callbacks depending on the command's
duration operand. The two Air Blast calls returning to `0x8008c204` used the
direct-set path. A fixed progress value therefore does not mean the camera
controller is inactive, and accelerating a shared script clock could move camera
events even if the interpolation routine remains unchanged.

The outer script dispatcher at `0x8008c590` delegates actor commands to
`0x8008b7f4`. That handler reads the script cursor at controller `+0x8c`; its
actor-command zero requests a clip, returns to the default clip, or polls the
control's completion notification depending on its operand. A blocked completion
poll rewinds the cursor by eight bytes at `0x8008bb14`, allowing the command to
be retried. This establishes an actual wait on model completion, rather than a
fixed duration guessed from the move's visible length.

For Patamon's basic attack, clip 15 completed and requested clip 16 in guest
frame 19,883; clip 17 completed and requested clip 18 in frame 19,953. Clip 19
completed at 20,093, with the default clip requested at 20,095. Clips 16 and 18
looped two and three times respectively before being replaced. Air Blast's clip
39 lasted 208 guest frames between selections, looped three times, and was
replaced without completion. Even a basic move mixes completion-driven and
externally released phases; clip IDs alone are insufficient for a speed policy.

No additional game process or always-on tracing was needed to analyze these
existing captures. The runtime and installed binary remain unchanged.

## Live script, damage, and resource audit — 2026-09-11

Fresh bounded captures now include script allocation leads, their callback
changes, script cursors/delays, shared damage results, and battle-local HP/MP.
The final basic and Air Blast traces retained 10,732 and 10,868 writes;
both recorded `total == available == saved entries`, with sequence and overlapping
byte-continuity validation. Local evidence is under `output/battle-events/`.

The normal graphics launch stalled before gameplay. A one-second host stack
sample found all 151 samples inside AMD's OpenGL context-creation path, with zero
main-thread CPU time during that interval. The stalled diagnostic process was
stopped; captures used the existing `PSX_HEADLESS=1` frontend, preserving normal
launch settings. This bypass allowed code/state tracing, **not** visual or audible
acceptance. Do not infer rendered hit alignment, sound pitch, or host performance
from these headless captures. No driver/system setting was changed.

### Script ownership and delay boundaries

In the basic fixture, `0x801345c8` changed from menu callback `0x80093e44`, through
`0x80098c9c`, to script callback `0x8008c590`. It reverted after the action.
The defender's script occupied `0x801350dc`; Air Blast instead used `0x800bdb28`.
The analyzer now closes/reopens script lifetimes on callback changes and ignores
unrelated writes in those allocations. Neither a prior header nor an address
from another move establishes current script ownership.

The explicit delay command initializes `+0x9c` at `0x8008c268`, subtracts elapsed
steps at `0x8008c28c`, then clears the wait at/below zero. Observed basic delays
were 15, 39, 39, and 39 units; Air Blast used 28, 50, 60, 10, and 100. These are
script-step units, not counts of model poses or host milliseconds.

The rewind at `0x8008bb14` is shared: actor command zero polls clip completion,
while actor command five also reaches it while waiting on its child controller.
The earlier label "completion poll" was incomplete without the command context.
The report now distinguishes those cases and separate effect/resource polling
at `0x8008bdd0`, `0x8008be74`, and `0x8008c438`.

Outer command 10 parses sound selectors at `0x8008c480` before dispatch toward
`0x8009b774` and the resident sound interface. Outer command 4 parses
effect/resource selectors at `0x8008c31c`. The reporter preserves the requested
selectors; 98/99 and the effect selector 56 can be resolved later from action
data. Repeated fetches can be polls, not repeated sound/effect starts. No raw
command stream or game asset is published with the tool.

### Prepared damage versus committed battle HP

The shared result record is at `0x800a43f4`, with damage at `+0x28`. Captured
stores `0x8009e234` (basic) and `0x8009e378` (technique) produce the result before
the corresponding attack/cast pose starts. The later action controller copies
the result before applying it to battle-local HP.

| Final capture | Damage prepared | First attack/cast clip selected | HP subtraction/clamp |
| --- | --- | --- | --- |
| Basic | 815 at guest frame 36,080 | Clip 15 at 36,160 | 36,416 |
| Air Blast | 440 at guest frame 43,805 | Clip 39 at 43,927 | 44,237 |

The six battle-local stat records start at `0x800a4470`, stride `0x20` (three
slots per side). Current HP is `+0x08`, current MP is `+0x0c`. In these captures,
Kunemon's current HP at `0x800a44d8` goes from 120 to a negative 16-bit intermediate
and then zero:

- Basic: subtract store `0x8008d064`, intermediate `0xfd49` (-695), clamp
  `0x8008d074`. This is 815 damage, not a second hit from the clamp.
- Air Blast: subtract store `0x8008fbc0`, intermediate `0xfec0` (-320), clamp
  `0x8008fbd4`, corresponding to 440 damage.

Air Blast spends MP earlier: store `0x80096de0` changes battle MP from 1231 to
1207 at frame 43,801, before damage preparation and casting. These battle-local
records are separate from the saved party records. A completed Air Blast replay
returned to the field with Patamon at 1207/1231 MP. A completed basic replay
matched all 7,904 party-record bytes of the prior reference result.

This supports isolating model timeline advancement from result preparation,
sound/effect dispatch, explicit waits, and HP/MP updates. It does **not** yet prove
that accelerating all poses preserves every visual hit or reaction. Keep damage
calculation/commit callbacks single-execution, retain marker crossings, and test
the guarded speed prototype against these independently observable boundaries.
All diagnostic processes were stopped; the installed runtime is unchanged.

## Next runtime work

1. Extend the verified timeline to additional actors, misses, recoil and
   multi-hit actions at 1x. Classify idle versus attack/recovery motion from
   controller ownership and action state, rather than hardcoding the observed
   Patamon clip IDs. Verify clip lengths and marker crossings for each case.
2. Use the script, damage, HP/MP and camera baselines above to compare a guarded
   model-only prototype. Extend visible/audible hit alignment and effect-frame
   checks when the graphical diagnostic launch is working again; do not treat
   headless event timing as that acceptance test.
3. Hook only the verified model timeline, with overlay/instruction validation and
   safe fallback to original playback. Use fractional accumulation for 1.25x and
   1.5x. Reset per-object state on clip changes, object reuse, load, and battle exit.
4. Preserve events crossed by an accelerated timeline exactly once. Equality
   checks against a skipped frame can drop a hit or effect; repeating whole battle
   callbacks can duplicate damage or consume extra RNG. Neither is acceptable.
5. Wire validated rates into the existing persisted settings bridge and menu
   once both action classification and playback are demonstrated to work.

Verification should compare a fixed-input battle at 1x and each accelerated
rate: damage, resource use, turn order, hit count, and rewards must match. Check
camera trajectory and duration, event alignment, visible pose transitions,
sound pitch, setting changes between actions, and checkpoint reloads. Include
basic attacks, techniques, misses, multi-hit attacks, recoil, defeat, and
digivolution before broadening the feature's supported scope.
