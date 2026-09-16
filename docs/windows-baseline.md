# Experimental Windows baseline

Shinka's Windows x64 build runs locally translated game code through the pinned
PSXRecomp runtime, with interpreter fallback. It is not a completed source
reconstruction. The optional expanded menu provides the portable Digimon Lab,
EXP/DV and encounter settings, soundtrack selection, camera options and battle
motion controls. See [current features and limits](../README.md#what-changes).

The historical movie probes below are superseded by the
[2026-09-10 movie and scheduler measurements](performance.md). The opening now
reaches full cadence in short samples, completes to the title screen, and skips
with Start. Longer-run stutter is improved but not fully resolved. Add
`-MovieNative` alongside `-OverlayCaptures` to reproduce the optional movie unit.

## Build from your own data

Requirements: Windows x64, Visual Studio 2022 with Desktop development with C++ and a Windows SDK, CMake 3.20+, Git, and Python 3.11+. The first configure downloads pinned SDL3, zlib, and libchdr dependencies. Use a normal developer terminal with access to the installed SDK.

Run the following from the Shinka repository root. Obtain the audited candidate
and its framework in a sibling directory:

```powershell
git clone https://github.com/Alexbeav/digimon-world-2003-recomp.git ../audit-recomp
git -C ../audit-recomp checkout 6ae36f9564b0c81b64428aa5355375d945d56d53
git -C ../audit-recomp submodule update --init psxrecomp
```

From the Shinka repository root:

```powershell
./tools/build_windows.ps1 -DiscBin 'PATH\TO\game.bin' -CandidateRoot ../audit-recomp
./tools/launch_windows.ps1 -DiscCue 'PATH\TO\game.cue'
```

The build checks the candidate/framework commits and the disc SHA-1 before extracting the boot executable. Generated code and assets stay local. The resulting executable is `build-windows/Release/dmw2003-shinka.exe`; use the launch script so configuration, disc, and separate save paths are supplied correctly. This is not yet a standalone distributable package.

To opt into the English expanded menu on the first launch, use:

```powershell
./tools/launch_windows.ps1 -DiscCue 'PATH\TO\game.cue' -EvolutionJournal -SaveDirectory 'output/player-saves'
```

This enables **DIGIVOLUTIONS** and **SETTINGS**; it does not choose boosted EXP
or an alternate soundtrack for you. Changes made in SETTINGS persist. Omit
`-EvolutionJournal` on later launches to keep the saved feature selection, or
pass `-EvolutionJournal:$false` to disable it while the game is closed. Alternate
soundtracks additionally need the [local music pack](music-live.md#local-build).
Use `-Jobs 2` on the build script to reduce compile concurrency on a busy laptop.

### Launching the executable directly

A double-click launch also needs the local disc and save-profile paths. A configured
shortcut can pass the same arguments as the launch script. Alternatively, add the
following sections to `settings.toml` beside the executable, substituting absolute
paths on your computer. Preserve any existing settings in that file. Include the
BIOS section only when using the optional retail BIOS backend described below.

```toml
[disc]
path = 'C:/Games/your-disc.cue'

[bios]
path = 'C:/Games/your-bios.bin'

[memcard]
dir = 'C:/Games/Shinka/output/your-existing-save-profile'
```

Use the folder containing your existing `card1.mcd` and `card2.mcd` to keep the
same saves. These machine-specific settings and shortcuts stay outside version
control. Without configured paths, a direct launch can fail before the disc
picker opens while Shinka initializes its disc-dependent modifications.

This is a per-machine setup, not an automatic first-run installer. A copy of
someone else's executable or shortcut will not discover your disc or cards.
The launch script supplies `--game`, `--disc` and `--memcard-dir` explicitly;
prefer it when verifying a fresh checkout. Moving the disc or profile requires
updating the shortcut arguments or these local settings.

### BIOS, controls and profiles

The default build includes the framework's OpenBIOS. An optional locally supplied SCPH-1001 BIOS with MD5 `924e392ed05558ffdb115408c263dccf` can be compiled and selected by passing `-RetailBios 'PATH\TO\bios.bin'` to **both** scripts. No retail BIOS is included. The completed movie/savestate probes used that optional backend; OpenBIOS reached language selection but has not had the same full smoke test.

Keyboard defaults: arrows = D-pad, Enter = Start, X/S/Z/A = Cross/Circle/Square/Triangle, Q/W/E/R = L1/R1/L2/R2, right Shift = Select. At language selection use **Start** to confirm. Default gamepad face buttons map A/B/X/Y to Cross/Circle/Square/Triangle.

See [controller compatibility](controller-support.md) for the native SDL3 input decision, optional mapping files, Steam Input path, and required hardware tests.

Optional normal EXP scaling is available through `-ExpMultiplier 1`, `2`, `3` or `4` on the launch script. See [configuration and battle comparisons](experience.md). Launch flags require the game to be closed; the expanded menu's SETTINGS entry can change normal and DV EXP rates during play.

Use `-SaveDirectory 'output/profile-name'` for a separate test profile. The default remains `output/player-saves`. See [copying DuckStation cards and loading profiles](save-profiles.md).

### Common first-launch issues

| Symptom | Check |
| --- | --- |
| Double-click exits before a game window appears | Run the launch script in a terminal with your own CUE path. Check the local path setup above rather than copying the maintainer's shortcut. |
| DIGIVOLUTIONS or SETTINGS is missing | Close the game, enable `-EvolutionJournal`, and use the supported English game. Reopen menus retained in old savestates. |
| Continue shows an empty card | Confirm the selected save directory contains your copied `card1.mcd`. A different profile has different cards and savestates. |
| An alternate soundtrack cannot be selected | Build and link the local music pack; SETTINGS reports **Music pack missing** when it is absent. |
| A controller opens but input does not reach the game | Focus the game window and check saved device selection and mappings in the [controller guide](controller-support.md). |
| Rebuilding cannot replace the executable | Close that game instance before building. Keep your normal player cards separate from diagnostic profiles. |

## Capture and compile overlays

The main executable does not contain all game code. Disc-loaded modules overwrite portions of its original RAM range. `game.toml` sets the overlay floor to physical `0x00082CB0`, based on the verified reward-module base; this enables the overlay path for that shared area. Other module loads still require validation.

The baseline includes a localhost debug server, default port 4380. Use another `-DebugPort` when running multiple instances. `-Headless` is available for framebuffer and audio-buffer probes.

```powershell
python tools/runtime_probe.py '{"cmd":"screenshot_file","path":"output/frame.png"}'
python tools/runtime_probe.py '{"cmd":"overlay_capture_dump"}'
python tools/runtime_probe.py '{"cmd":"quit"}'
```

Wait for the process to exit before rebuilding. At the audited framework revision, the capture JSON is written beside the executable as `build-windows/Release/overlay_captures.json`. Captures contain game bytes and must remain ignored.

```powershell
./tools/build_windows.ps1 -DiscBin 'PATH\TO\game.bin' -CandidateRoot ../audit-recomp -OverlayCaptures build-windows/Release/overlay_captures.json
```

Supply the same optional `-RetailBios` choice as the first build. This generates a local `output/overlays/overlays_static.c` and links it with MSVC; GCC is not needed for this static route. Omitting `-OverlayCaptures` explicitly disables the optional overlay source on the next build. The generated dispatcher validates current RAM code before running a captured implementation. Unseen or changed code falls back to the interpreter.

## Early validation record

This section preserves the initial baseline observations. For current movie and
battle measurements see [runtime profiling](performance.md); card read/write
batching and compatibility checks are in [save timing](save-timing.md). The
[project status](../README.md#status) summarizes current coverage and limitations.

The first user playthrough exited at the registration/partner-selection transition. A replay reproduced stale native-overlay execution; Shinka's live-byte guard now rejects it. The corrected build passes that checkpoint through name entry, starter-pack selection, and completed registration. See [failure evidence and correction](partner-selection-exit.md). Other progression and performance checks remain open.

- Main EXE: 23 translated C shards, 1,230 dispatch entries. These counts do not measure decompilation completeness.
- Windows Release compilation and linking succeeded with MSVC 14.44 and SDK 10.0.26100.0.
- Language screen rendered; D-pad changed selection; Start entered the opening movie.
- Opening movie frames advanced, and SPU/CD audio buffers contained nonzero samples at 44.1 kHz. Headless audio-buffer activity alone does not validate speaker playback or audio synchronization.
- A separate windowed run created an OpenGL 3.3 context, initialized the GPU pipeline, restored a movie state, and sent nonzero audio to the active host output at 44.1 kHz. The audio diagnostics reported underruns and overflow drops; smooth, synchronized listening is not established.
- The user confirmed hearing the opening movie through speakers, describing it as very jittery. Audible output is confirmed; playback quality remains a failure.
- Native savestate save/load succeeded during the movie. Blank local memory-card files were created. This does not establish in-game card save/load compatibility.
- After the overlay fix, the user reported that Central Park, a normal battle, the gym, and shops worked. These are user playtest results; broader progression coverage remains open.
- The user reported successful in-game saving/loading and savestates, with slow card save/load screens. Disk inspection confirmed a 128 KiB card with an allocated `BESLES-03936DMW3-EUR` entry (32 KiB). A stable-read backup is preserved locally under `output/save-backups/first-guardromon-save/`.
- A subsequent agent-controlled test used copied cards in `output/performance-saves/`, restored the inn checkpoint, traversed Asuka City, Asuka Bridge and Central Park, and triggered a Kunemon encounter in Wire Forest Entrance. The battle scene, party switching and combat ran, followed by return to a responsive field. The reward/result screen was not separately captured. Local diagnostic slots 2, 3 and 4 preserve the park, battle-entry and post-battle states; `output/encounter-entry.png` and `output/encounter-return.png` record the endpoints. This is one encounter, not broad combat coverage.
- An initial Guardromon overwrite trace observed 80 successful sector writes spanning approximately 29 seconds while the guest ran at 50 frames/second. The Saved message appeared around 30 seconds. This was the unmodified baseline, before the subsequent [read/write batching work](save-timing.md).
- The initial overlay-fallback movie run measured approximately 0.31–0.34 times real time. The lowered overlay floor allowed interpreter-local chaining; performance remains a validation target.
- First static overlay generation processed six retained capture regions: five built, one skipped for lack of walk-root seeds, zero failures, 325 exact function identities. This capture covers only paths visited during boot/movie playback.
- The overlay-enabled executable linked, restored the movie savestate, and continued rendering. Its static-overlay validator reported 186,277 successful dispatches at one snapshot. The generic `dispatch_native` counter counts the dynamic DLL route and stayed zero; use `static_hits` in `overlay_loader_status` for this build. Short diagnostic timing samples rose to roughly 0.48–0.57 times real time, still below the target and not a controlled benchmark.

Title flow, new-game progression, exploration, battle entry/exit, audible playback, in-game saving/loading, and full-speed sustained play must all pass before the Windows baseline milestone is complete. Keep ordinary player saves separate from diagnostic savestates and use copies when importing emulator cards.

The framework is pinned to `f3786825411983a06257865db7bd7538fc68267a` under PolyForm Noncommercial; the candidate wrapper is GPL-3.0 and the UI is a separately licensed component excluded from this build. See the [groundwork audit](groundwork-audit.md) for source and licensing boundaries. Generated game/BIOS code and original assets are not tracked in Shinka.
