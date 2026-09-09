# Battle EXP multiplier

The first EXP feature scales the normal battle reward table by 1, 2, 3 or 4.
Scaling happens **before** the original participation split and rounding. It
does not enable reserve EXP, change BIT rewards, or change Digivolution EXP and
its cap. For split rewards, rounding means the final displayed award need not
be exactly the multiplier times the original rounded award.

## Usage

Build the current Windows runtime, then close it before changing the setting:

```powershell
./tools/launch_windows.ps1 -DiscCue 'PATH\TO\game.cue' -RetailBios 'PATH\TO\bios.bin' -ExpMultiplier 3
```

`-ExpMultiplier 1` disables the feature. Omitting the parameter retains the
previous setting. `-Python 'PATH\TO\python.exe'` selects a Python 3.11+ runtime.
There is no in-game settings entry yet.

To configure without launching:

```powershell
python tools/configure_exp.py --disc-bin 'PATH\TO\game.bin' --multiplier 3
```

The generator verifies the supported BIN hash and reward-overlay hash, locates
the overlay through the ISO directory catalog, and generates a local declarative
package under `build-windows/Release/mods/`. It preserves unrelated mod selections
and backs up the previous state file. No input disc bytes are changed. Generated
patch manifests contain disc-derived expected values and remain ignored.

The runtime checks the exact disc hash and each original field before applying
patches to disc reads. Original game code still performs the award, level-up and
save operations. Restoring a state that already contains the reward overlay may
retain its old reward values; use a pre-reward battle checkpoint or a normal
card save when comparing settings. Disabling the feature does not undo EXP
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
