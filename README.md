<p align="center">
  <img src="assets/shinka.png" alt="Shinka emblem" width="160" height="160">
</p>

<h1 align="center">Digimon World 2003 — Shinka</h1>

<p align="center">
  <a href="https://github.com/JohnnySn0w/dmw2003-shinka/actions/workflows/tests.yml"><img src="https://github.com/JohnnySn0w/dmw2003-shinka/actions/workflows/tests.yml/badge.svg?branch=main" alt="Python tests"></a>
  <a href="https://github.com/JohnnySn0w/dmw2003-shinka/actions/workflows/lint.yml"><img src="https://github.com/JohnnySn0w/dmw2003-shinka/actions/workflows/lint.yml/badge.svg?branch=main" alt="Python lint"></a>
  <a href="https://github.com/JohnnySn0w/dmw2003-shinka/actions/workflows/coverage.yml"><img src="https://github.com/JohnnySn0w/dmw2003-shinka/actions/workflows/coverage.yml/badge.svg?branch=main" alt="Python coverage report"></a>
  <a href="docs/windows-baseline.md"><img src="https://img.shields.io/badge/platform-Windows%20x64-0078D4" alt="Platform: Windows x64"></a>
  <a href="#status"><img src="https://img.shields.io/badge/status-experimental-orange" alt="Status: experimental"></a>
</p>

Mod development for Digimon World 2003, targeting the European multilingual PlayStation release (`SLES-03936`).

## Status

An experimental Windows x64 build supports the tested early-game exploration, battles, shops, gym and saves. Main-executable code and captured overlays compile locally through the pinned PSXRecomp framework, with interpreter fallback. Campaign coverage remains incomplete, and movie playback is jittery.

The first gameplay feature is optional **1–4x normal battle EXP**, applied through guarded disc-read patches. See [EXP configuration and validation](docs/experience.md). Money is unchanged; the expanded field menu now includes live EXP settings. See the [progression formulas](docs/progression.md) and [menu/map groundwork](docs/menu-map.md).

An experimental English menu adds **DIGIVOLUTIONS** and **SETTINGS** as selectable rows in both the world overlay and the full-screen root reached after leaving a submenu. Enable it with `python tools/configure_journal.py --enable` and restart. DIGIVOLUTIONS opens the full lab interface for switching partners, selecting battle forms, loading techniques and viewing the chart; leaving it highlights DIGIVOLUTIONS again. Select an anonymous chart node and press X for directional training hints. SETTINGS includes live EXP controls and **0%, 50%, 100%, 150%, 200% random encounter rates**. See [menu controls and implementation](docs/field-menu.md), [encounter behavior](docs/encounters.md) and [lab integration](docs/evolution-journal.md).

SETTINGS also includes [Battle motion](docs/battle-animation-speed.md), with independent
1x, 1.25x, 1.5x and 2x idle and action pose speeds. Both default to 1x. Camera and script delays
keep their own timing; action poses include attacks and reactions.

SETTINGS also offers experimental [battle camera controls](docs/camera.md):
**4:3 / 16:9 view** and independent **100% / 90% / 80% zoom**. Field areas retain
their original view while their tile-streaming requirements are investigated.

See [Windows build, launch, and overlay-capture instructions](docs/windows-baseline.md) for the runnable baseline and current validation limits.

See [runtime profiling](docs/performance.md) for GPU selection, CPU measurement
tooling, initial field/battle observations, and the next optimization targets.
An optional guarded native battle-geometry unit reduced process CPU cost by
31% in the tested battle; `-BattleNative` enables it during scripted builds.
`-MovieNative` adds the audited opening-movie decoder/transfer routines. Together
with cheaper audio scheduling and exact live-byte comparisons, movie samples
improved from roughly 33 to 50 guest updates per second; longer playback still
has occasional dips. See the profiling report for measurements and limits.
Windows Release builds also optimize across the device implementations and use
short high-resolution sleeps to reduce frame-limiter busy-waiting. The latest
movie sample used about 3.5% less CPU per update; this remains incremental work.
A subsequent CD deadline correction removed roughly 460,000 redundant scheduler
queries/sec in a matched movie sample, reducing CPU cost another 2.7%. The
[runtime timing map](docs/runtime-timing-map.md) records the finding, movie data
path, acknowledgement rules and tools for future investigations.

The portable evolution chart remembers your last branch separately for each
partner during the session. Loading a savestate preserves that state's own
chart selection instead of applying a previous session bookmark.

The original map now offers **X: Travel** between eleven visited Asuka-server locations:
Asuka City bridge, Central Park, Wire Forest Entrance, Wire Forest, Seiryu City,
South Station, Bulk Bridge, Tranquil Swamp, Phoenix Bay, Suzaku City and Pelche Oasis.
Travel cuts directly from the map into the original area loader. South Sector
station/swamp stops require the first arrival scene to be complete and South Station visited.
Suzaku requires Zanbamon's removal and preserves its introduction, Kail's return,
and the later Phoenix Bay earthquake through conditional arrivals and departures.
Asuka's Main Lobby cannot be used to teleport out during the city lockdown; its
outside bridge remains available. See
[availability rules and current coverage](docs/menu-map.md).

Existing DuckStation memory cards can be copied into isolated test profiles; see [save imports and profile selection](docs/save-profiles.md).
Memory-card transfers now use larger batches: the tested save body loads in about 6 seconds instead of 25, and saving takes about 8 seconds instead of 29. Per-sector checks and disk flushes are retained. See [timing and validation](docs/save-timing.md).

The [developer navigation tool](docs/developer-navigation.md) provides named
warps, position bookmarks, measured movement, routes and checkpoints, plus
explicit story/quest and HP/MP/strength edits for testing in copied profiles.

See the [groundwork audit and port milestones](docs/groundwork-audit.md) for pinned sources, verified findings, feature analysis, and reproduction commands.

The [offline music exporter](docs/music.md) converts owned BGM packs into MIDI,
sample WAVs with loop points, and instrument metadata. All 30 BGM pairs export
successfully. [Offline soundtrack auditions](docs/music-palettes.md) render
BGM001 with CC0 sampled instruments, a 24-voice oscillator-chip palette, or the
preferred **DS-inspired hybrid** of samples and synth accents.
The [per-track listening guide](docs/music-listening-guide.md) identifies 41
sequences with scene context and arrangement questions. The current BGM001
auditions are **Asuka City**; other track arrangements are still pending.
[Live soundtrack switching](docs/music-live.md) now uses that SETTINGS preference:
**Original, DS, Sampled, or Chip** changes music instruments mid-song. The local
pack covers 42 music banks with provisional sample-level arrangements; effects,
ambience and unidentified banks keep their original audio.

## Checks

The badges track the Python tooling's [tests, lint checks and coverage reports](docs/testing.md).
The coverage badge shows report-job status; measured percentages and per-file results
are in that run's summary and downloadable report. These checks use synthetic test
data and do not require a game disc. Native regression tests and in-game validation
are separate local checks; Python coverage does not measure campaign or emulator coverage.

## Planned work

- Expand EXP validation across party splits, later enemies and progression caps.
- Expand DV validation across later forms, participation splits and natural growth limits.
- Refine the DS-inspired soundtrack direction and resolve track/loop/controller behavior before integrating optional playback.
- Expand advanced-party coverage for DIGIVOLUTIONS and its session partner retention; see [design and hint groundwork](docs/evolution-journal.md).
- Expand the initial map travel network with validated destinations and later story/server access rules.

Fresh configurations retain original EXP until enabled. The current local setup selects 3x normal EXP and fixed 10-point DV awards.

## Local game data

Use a local disc dump as input. Keep the original unchanged; the EXP feature patches reads at runtime. Disc images, extracted assets, generated manifests and emulator saves are excluded from Git. This repository contains source, documentation and patch-generation logic rather than game data.

The current disc dump lives outside this repository, in a sibling directory. Future tooling should accept an explicit input path rather than depend on a machine-specific location.

See [investigation notes](docs/investigation.md) for findings and open questions.

The [combat model audit](docs/combat-models.md) documents the native mesh format,
local OBJ/texture export tooling, and an offline smoothing prototype.
