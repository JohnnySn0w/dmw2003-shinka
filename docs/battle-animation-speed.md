# Battle animation speed investigation

Status: static investigation, 2026-09-10. No animation speed hook or menu setting
is enabled yet. Work resumed after the user's CPU-heavy task cleared; the
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

## Static findings and unresolved candidates

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

## Next runtime work

1. Use the copied diagnostic battle checkpoint, with all rates at 1x. Trace model
   pose advancement during idle, a basic attack, and a technique. Identify the
   owning object, frame accumulator, clip length, and action classification.
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
