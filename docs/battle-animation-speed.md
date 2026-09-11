# Battle animation speed investigation

Status: live model-timeline audit, 2026-09-11. No animation speed hook or menu
setting is enabled yet. Work resumed after the user's CPU-heavy task cleared; the
[battle geometry optimization](performance.md) reduces execution cost without
changing animation speed. Its rendering routines are not yet an identified
model-animation clock.

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
Camera trajectory ownership still needs a separate behavioral audit.

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

## Next runtime work

1. Extend the verified timeline to additional actors, misses, recoil and
   multi-hit actions at 1x. Classify idle versus attack/recovery motion from
   controller ownership and action state, rather than hardcoding the observed
   Patamon clip IDs. Verify clip lengths and marker crossings for each case.
2. Trace camera motion independently and locate hit, effect, sound, and recovery
   events. Compare pose progress with action-script progress to identify shared
   clocks and waits before changing either.
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
