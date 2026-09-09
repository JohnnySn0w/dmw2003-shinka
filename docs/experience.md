# Battle and Digivolution EXP multipliers

The first EXP feature scales the normal battle reward table by 1, 2, 3 or 4.
Scaling happens **before** the original participation split and rounding. It
does not enable reserve EXP or change BIT rewards. Independent DV scaling
multiplies the final DV award after original rounding, minimum and caps. For split rewards, rounding means the final displayed award need not
be exactly the multiplier times the original rounded award.

## Usage

Build the current Windows runtime, then close it before changing the setting:

```powershell
./tools/launch_windows.ps1 -DiscCue 'PATH\TO\game.cue' -RetailBios 'PATH\TO\bios.bin' -ExpMultiplier 3 -DvExpMultiplier 3
```

`-ExpMultiplier 1` disables normal scaling; `-DvExpMultiplier 1` disables DV
scaling. Omitting either parameter retains its previous setting. `-Python 'PATH\TO\python.exe'` selects a Python 3.11+ runtime.
There is no in-game settings entry yet.

To configure without launching:

```powershell
python tools/configure_exp.py --disc-bin 'PATH\TO\game.bin' --multiplier 3 --dv-multiplier 3
```

The generator verifies the supported BIN hash and reward-overlay hash, locates
the overlay through the ISO directory catalog, and generates a local declarative
package under `build-windows/Release/mods/`. It preserves unrelated mod selections
and backs up the previous state file. No input disc bytes are changed. Generated
patch manifests contain disc-derived expected values and remain ignored.

The runtime checks the exact disc hash and each original field before applying
patches to disc reads. Original game code still performs the award, level-up and
save operations. Restoring a state that already contains the reward overlay may
retain its old code or reward values. Even a battle-entry state can contain
prefetched reward code: restart and load a normal memory-card save after changing
DV settings. A menu round trip is not sufficient to invalidate that prefetch. Disabling the feature does not undo EXP
already earned and saved.

## Reconstruction evidence

In the verified European `STFGTREP.PRO`, the reward table starts at file offset
`0x3dd8` (RAM `0x80086a88`). It contains 335 records of three 32-bit words.
Normal EXP loads use record offset `+4`; the DV path uses `+0`, and the BIT path
uses `+8`. The original overlay's SHA-256 is
`c2e8845fccab5f2e852c1025fac2ee4f548c6136b1a1b47e6c838ce7eb5f1ef9`.

Normal EXP reads occur at overlay offsets `0x2cf8`, `0x2d28` and `0x2d70`.
The one-participant path uses the base value; two participants use the original
six-tenths calculation, and three use the original integer division by three.
Participation flags and those instructions are untouched. The maximum base EXP
in this image is 2,365; even at 4x its intermediate multiplication by six fits
signed 32-bit arithmetic. The generator also rejects arithmetic overflow.

The inspected ddw3 assembly/data supplied the layout lead; the local overlay
bytes, call sites and runtime battle are the verification sources. No ddw3
implementation is included.

## Runtime integration

The pinned frontend commits mods before resolving the CLI disc when its setup
launcher is disabled. Shinka's CMake configuration generates a local frontend
copy whose initial commit uses an explicit `--disc` argument when supplied.
The dependency checkout remains unchanged, and the original hash guards remain
mandatory. Configuration fails if the expected upstream call site disappears.

The package remains marked as a developer feature while battle and progression
coverage expands. Automated checks cover all four factors, untouched DV/BIT
fields, sector boundaries, revision rejection, arithmetic overflow, preserving
other mods, and disabling the feature.

## Battle comparison — September 9, 2026

Each replay restored the same copied Kunemon battle checkpoint. A diagnostic
HP/MP refill allowed Kumamon to finish it with Bear Fist; it did not change EXP
or reward data. Only Kumamon participated. The user's original cards remained
untouched. Local screenshots and RAM captures are in `output/exp-*`.

| Setting | EXP awarded | Kumamon total after award (started at 10) | Level after award |
| --- | --- | --- | --- |
| Original | 6 | 16 | 2 |
| 2x | 12 | 22 | 2 |
| 3x | 18 | 28 | 2 |
| 4x | 24 | 34 | 2 |

Selecting 1x again and restarting restored the 6-EXP reward and original live
reward table. The local setup was then left at 3x for the next launch.

The live Kunemon reward record retained DV input 1 and BIT input 10 in each
multiplied run. No evolved forms participated, so this is not a DV-award test.
The cumulative EXP field was independently read at `0x80049890` after awarding
2x/3x/4x, in addition to inspecting the reward and level-up screens.

Two integration problems were resolved during the comparison: the CLI disc
commit ordering above, and the framework build step pruning locally generated
packages from its staging directory. The generator now keeps an ignored source
manifest in `output/exp-mod/`; Shinka stages it after the framework catalog.
The initial unchanged-reward runs lacked that package and are not evidence of
a savestate prefetch bug. The battle checkpoint worked after staging was fixed.

Remaining coverage includes two/three participating rookies, evolved forms,
level caps, multiple level gains, later enemies, and a card save/reload of
multiplied progression. These are not implied by the early-game comparison.


## Independent DV multiplier

The guarded 16-byte delivery call at overlay offset `0x1388` originally loads
its function pointer, waits one instruction, calls it, and moves the calculated
award into argument register a2 in the call's delay slot. The 3x patch uses the
wait slot for `a2 = v0 << 1` and the delay slot for `a2 += v0`. The pointer load,
call, and other registers remain unchanged. 2x and 4x use a single shift in the
delay slot. No enemy DV fields or normal EXP fields are altered by this feature.

Scaling after the original cap is intentional: an original award of 10 becomes
30 at 3x, rather than hitting the original cap again. The original accumulation,
level-up, carry-over and maximum-level checks still run. See
[progression formulas](progression.md) for the differing curves and later-form
natural limits.

A controlled replay used level-5 Kumamon with Grizzmon participating alone
against Kunemon. Original DV total went from 0 to 2; the 3x instructions changed
it from 0 to 6. The old checkpoint contained prefetched original code, so the
comparison explicitly replaced that guarded 16-byte code span in the diagnostic
RAM copy before the game loaded it. This checks execution and award behavior,
not fresh disc-read integration. Original player memory cards were untouched.

Automated instruction checks cover final awards 1-50 for all modified factors
and verify preservation of other registers. Settings tests ensure normal and DV
selections do not overwrite each other. Live later-form, participation-split,
multiple-level and DV save/reload coverage remains outstanding.

A fresh runtime also loaded the copied normal memory-card save successfully.
No evolved-form battle was completed from that fresh load; the live 2-to-6 DV
comparison above remains the controlled checkpoint test, not a cold-load battle
comparison. Seventeen Python tests pass. The local configuration is left at 3x
normal EXP and 3x DV EXP.


## Fixed 10-point DV mode

`-DvFixed10` in the Windows launcher, or `--dv-fixed-10` in the Python
configuration command, replaces the final award with exactly 10 DV points for
each eligible participating form. This mode replaces DV multiplication; the CLI
rejects specifying both. Normal EXP remains independently configurable.
Selecting `-DvExpMultiplier` again switches back to multiplier mode (1 disables
DV modification). Omission preserves the current choice.

The patch leaves the pointer load, wait slot and call intact, replacing only
its delay-slot argument assignment with `addiu a2,zero,10`. Manifest conditions
make fixed and multiplier patches mutually exclusive. Existing configurations
without the new option default to multiplier mode.

With consistent original progression data, 10 points gives one skill level per
battle below the natural growth limit, and one per five battles above it. Any
partial progress carries over; level 99 remains the maximum. This is not an
at-least-10 floor: a naturally larger award is also replaced with 10.

Validation covers guarded instruction generation, exclusive patch selection,
switching modes, and preservation of normal EXP. Fixed mode has not yet received
a live battle test. The local setting now uses normal EXP 3x plus fixed DV 10.
