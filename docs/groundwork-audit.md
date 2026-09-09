# Groundwork audit — 2026-09-08

## Decision

Target a Windows port with progressively reconstructed, readable game systems. Use a recompilation runtime as a candidate bridge, not as evidence that a full decompilation is complete. Preserve the original presentation and behavior first; introduce optional mechanics changes after a reliable baseline exists.

The audit completed source inspection, local disc extraction, Windows builds of the recompiler tools, static analysis, and generation of C from the main executable. **No playable Windows game has been built or tested.** Main-executable translation does not cover the game's streamed code overlays or prove correct execution.

## Repositories inspected

These revisions pin the observations below. Checkouts are local siblings of Shinka, not vendored or published in this repository.

| Project | Revision | Finding and intended use |
| --- | --- | --- |
| [markisha64/ddw3](https://github.com/markisha64/ddw3) | `b125b3d7471c23d305b27f0b1d7a2353643a3ee3` | Most useful reverse-engineering reference: assembly, typed gameplay data, asset parsers, overlay layout. Not a finished source port. |
| [Alexbeav/digimon-world-2003-recomp](https://github.com/Alexbeav/digimon-world-2003-recomp) | `6ae36f9564b0c81b64428aa5355375d945d56d53` | Reproducible translation candidate. Game-specific symbol map contains only a guessed BootEntry, with `emit=false`; seeds contain 492 scanned addresses. |
| [Alexbeav/psxrecomp](https://github.com/Alexbeav/psxrecomp) | `f3786825411983a06257865db7bd7538fc68267a` | Pinned framework from the above project. Game/BIOS emitters and analyzer build successfully with local MSVC. Includes hardware runtime and interpreter fallback. |
| [Xive080/D-W-3-Recomp](https://github.com/Xive080/D-W-3-Recomp) | `e7c2cd48e1a15a93aeafe543f4e3bdc7b40a3243` | Checked-out public tree is documentation, mod metadata/packages, and bug-report assets. No native engine source or root build project found. Cannot reproduce its advertised native port from this checkout. |
| [markisha64/dmw_2003_patcher](https://github.com/markisha64/dmw_2003_patcher) | `807e01511b3034d64dfadc067c8f90e90c1817ed` | Rust patch composer and separate patch submodules. Useful behavioral references; not a port. Only relevant encounter/DV submodules fetched. |
| [RichardPacco/DMW2003-Exp-Share](https://github.com/RichardPacco/DMW2003-Exp-Share) | `83bd140fa41f929dc5367c52555f254ae5637c43` | Concrete signature and reward-participation routine. Signature matched exactly once in our extracted reward overlay. |

The additional `mateusgiordani/ddw3-decomp-expanded` reference credited by Xive could not be retrieved: Git returned authentication failure. Its availability and contents remain unverified; no dependency on it is assumed.

### ddw3: what is actually usable

- `rust/types/src/digimon_profile.rs` defines a 0x58-byte profile containing stats, resistances, move slots, growth fields, and Blast information, with remaining unknown fields explicit.
- `rust/dw2003_pro_stfgtrep/src/data.rs` labels evolution tables. `asm/dw2003/pro/stfgtrep.s` contains the reward routine that matched our image.
- `tools/ddw3-uniso` supports path-table extraction, explaining how to reach directories missing from the root listing.
- `tools/ddw3-vab-sep` and `tools/extract_all_sound.sh` describe sequence and instrument extraction.
- The build targets PS1 and requires nightly Rust, MIPS GNU binutils, zbuild, mkpsxiso, and Unix-style utilities. A full ddw3 build was not attempted; this is not the Windows runtime build path.
- Overlay metadata varies in quality: `STFGTREP.PRO` has load address `0x80082cb0`, but `STSTATUS.PRO` has an explicit placeholder `0x80000000`. Do not use that placeholder as a real address.
- No repository-wide source license was located in the tracked tree. Treat it as an inspection reference until reuse terms are established, rather than copying its implementation into Shinka.

### Recompilation candidate: strengths and gaps

The configured image hashes match our disc. The three C++ tools compile on Windows with MSVC 19.44.35221 and the installed Windows SDK. The setup executable-name consistency test passes.

Generation with the original seed file and `--strict` succeeds, yielding 23 C shards and a dispatch table with 1,230 entries. These are generated translation artifacts, **not a count of understood game functions or a decompilation percentage**. The emitter reports out-of-function control-flow warnings. Static analysis output is saved locally for investigation.

The framework documents an interpreter fallback for runtime-installed/streamed code and capture/compile/cache support. Consequently, a resulting Windows executable can still emulate parts of PS1 execution. Our eventual goal is to replace understood game systems with native implementations while retaining behavior; this audit does not establish full native coverage.

The game wrapper has no implemented option rows or rich game-specific symbol annotations. Full runtime linkage, graphics, sound, save/load, overlay transitions, and campaign completion are untested. The UI submodule was not fetched for this emitter-only probe.

License files identify the game scaffold as GPL-3.0-only, PSXRecomp as PolyForm Noncommercial 1.0.0, and the UI as separately licensed. Preserve boundaries and attribution if adopting these dependencies; do not relabel the whole stack as one uniformly licensed codebase.

### Xive and existing mod packages

The public checkout's FastTravel documentation describes exactly the proposed interaction: press X on a map icon and travel on fully closing the menu. It also says visited locations are used and Square changes server maps. Its post-game behavior allows travel beyond intended boundaries; descending underground or underwater there can hang. This is a known upstream warning, not a locally reproduced result.

The packaged map and battle changes include replacement `.PRO` assets. They were not copied into Shinka or applied to the disc. Public documentation and packages do not establish a reproducible native engine. Keep this project as a feature/behavior reference unless buildable source becomes available.

## Verified local disc and asset findings

See [machine-readable evidence](evidence/disc-summary.json).

- BIN size: 692,146,560 bytes, single-track MODE2/2352.
- SHA-1: `457cb233349ba841e03b33d8060f8fbcadd45cb3`.
- SHA-256: `fb70dc9a995aed628cf515cabc87c7b14e5142559076ec394dfe793ec3e26a04`.
- Boot entry `0x80010e90`, load address `0x80010000`, text length `0xe1000`, stack `0x801ffff0`.
- 98 path-table directories and 2,481 directory entries, including directory records; this is not 2,481 unique asset files.
- Successfully extracted the boot executable, `STSTATUS.PRO`, `STFGTREP.PRO`, and the two BGM001 packs into ignored local storage.
- `MPBGM001.BIN` contains `pBAV` at offset 8 and `pQES` at offset 8,744. Its first two pack offsets are 8 and 8,744. `MVBGM001.BIN` begins with a body offset of 4. This directly supports the sequence-plus-sample-bank finding for our own image. Playback/conversion was not tested.
- EXP-share's original 120-byte signature occurs once in `STFGTREP.PRO`, offset `0x2c44`; adding its documented load base gives `0x800858f4`.
- The encounter-disable IPS changes boot-EXE file offset `0x3331c` from `01` to `00`. This is a lead for locating the encounter control flow, not a proportional rate slider.
- The DV-cap IPS contains an RLE record replacing 56 bytes at reward-overlay offset `0x3d80` with zeros. It changes code, not just a single limit constant. Its behavioral correctness and caps still need tracing.

No disc modifications were applied. The original input was opened read-only.

## Engine assessment

The observed architecture is a main MIPS executable, dynamically loaded `.PRO` code, packed assets, PlayStation graphics formats, and sequenced sample-bank audio. This requires a platform runtime or replacement platform services for Windows. No named commercial engine or definitive in-house-engine attribution was established. Architecture observations should not be promoted into a historical engine claim.

## Planned feature audit

The first four rows capture explicit user requests. The rest remain design candidates, not automatically approved gameplay changes.

| Feature | Groundwork found | Remaining work / acceptance condition |
| --- | --- | --- |
| 2–4× EXP | Reward overlay, participation signature, typed progression data | Trace award calculation and rounding; separate base EXP, DV EXP, and money. Verify 2×/3×/4× known rewards, level-ups, and overflow behavior. |
| Map-icon teleport | Existing FastTravel behavior and status overlay identified | Recover map selection, real overlay load address, area-transition interface, visited flags, server/story restrictions, and safe spawn points. Test both servers, post-game, water/underground, cancel, and save/reload. |
| In-menu encounter adjustment | Verified binary location of existing disable patch | Trace distance/counter/probability logic. Add 0/50/100/150/200% control without changing scripted fights. Define zero-rate counter behavior and persistence. Verify statistically over fixed travel routes. |
| Optional richer instruments/music | Actual BGM001 sample and sequence pack headers found | Decode one song and verify timing, loops, program mapping, and reverb. Keep original music as baseline; assess modern synth or recorded replacement at the native audio layer. |
| Reserve EXP / catch-up | Exact EXP-share signature; 12 participation flags described upstream | Establish splitting rules and distinguish base and form growth; avoid multiplying total awards accidentally. Catch-up formula is still a design choice. |
| Faster battle presentation | Battle overlay and upstream speed-up package | Separate visual delays from turn/RNG logic and music rate. Compare fixed-input battle outcomes. |
| Visible evolution requirements | Labeled evolution data | Decode remaining conditions and expose accurate UI; preserve unlock behavior at defaults. |
| Technique/MP/DNA balance | Typed move/profile fields | Recover combat formulas and collect baseline outcomes before changing values. No balance proposal is final. |
| Player-controlled Blast | Profile contains Blast fields | Locate gauge, trigger, duration, and reset state. New input/menu work; no verified trigger hook yet. |
| Training/navigation improvements | Training data and localization tooling | Specify desired behavior first. Not part of the initial port milestone. |

## Port milestones

1. **Input and provenance — achieved for the supplied image.** Repeatable read-only inspection, exact hash, boot/selected-overlay extraction, pinned upstream revisions.
2. **Translation probe — achieved for the main EXE only.** Build emitters and produce local C plus static analysis. This is not a runnable game.
3. **Windows baseline — next implementation milestone.** Link the candidate runtime; boot to title, start a game, walk, enter/exit battle, play original audio, and save/reload. Keep Shinka features off. Record failures and interpreter coverage rather than accepting a title screen as success.
4. **Readable system reconstruction.** Establish validated types, function names, memory ownership, and overlay identities. Start with reward calculation and map/menu transitions. Each translated/replaced routine must be compared with the original under controlled inputs.
5. **Feature slices.** EXP first; encounter control second; guarded map teleport third. Test default settings for unchanged behavior and enabled settings for their intended effect.
6. **Presentation and broader mechanics.** Optional audio replacement, battle timing, progression UI, and balance changes once the baseline is reliable.
7. **Release validation.** Progression checkpoints throughout both servers and post-game, save compatibility or explicit migration, reproducible user-data import, and packaged Windows smoke test.

## Reproduction

Python 3 standard library is sufficient for Shinka's inspection tool. From the repository root:

```powershell
python tools/audit_disc.py 'PATH\TO\game.bin' --output extracted/audit --extract-exe --extract-file STSTATUS.PRO --extract-file STFGTREP.PRO --extract-file MPBGM001.BIN --extract-file MVBGM001.BIN
python -m unittest discover -s tests -v
```

For the pinned local candidate checkout (replace `AUDIT_RECOMP` with its path), the successful MSVC tool build was:

```powershell
cmake -S AUDIT_RECOMP/psxrecomp/recompiler -B AUDIT_RECOMP/build-recompiler -G 'Visual Studio 17 2022' -A x64 -DPSXRECOMP_ENABLE_CHD=OFF -DBUILD_TESTING=OFF
cmake --build AUDIT_RECOMP/build-recompiler --config Release --target psxrecomp-game psxrecomp-bios psxrecomp-analyze --parallel 4
& AUDIT_RECOMP/build-recompiler/Release/psxrecomp-game.exe extracted/audit/SLES_039.36 --project-root AUDIT_RECOMP --seeds AUDIT_RECOMP/seeds/ghidra_funcs.txt --out-dir output/recompiled --strict
& AUDIT_RECOMP/build-recompiler/Release/psxrecomp-analyze.exe extracted/audit/SLES_039.36 --seeds AUDIT_RECOMP/seeds/ghidra_funcs.txt --out output/analysis --emit-tsv output/analysis/functions.tsv --quiet
```

The initial sandboxed MSVC configure failed on access to the installed SDK's user directory. Running it with normal host access succeeded; this was an environment permission issue, not a compiler incompatibility. The first emitter invocation without `--project-root` could not find its BIOS profile; supplying the candidate root resolved that. No retail BIOS dump was required for this main-EXE generation probe.

Three synthetic-image tests passed: extraction with source preservation, rejection of a truncated image, and rejection of path traversal in selected filenames. The live-image audit also succeeded. These checks validate the inspection utility, not gameplay or the upstream runtime. Git ignore checks confirmed that extracted executable and generated game C are excluded.

Generated game code, extracted content, and build outputs remain ignored. This audit does not redistribute upstream game assets or claim generated code is newly authored Shinka source.
