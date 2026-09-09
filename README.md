# dmw2003-shinka

Mod development for Digimon World 2003, targeting the European multilingual PlayStation release (`SLES-03936`).

## Status

An experimental Windows x64 build supports the tested early-game exploration, battles, shops, gym and saves. Main-executable code and captured overlays compile locally through the pinned PSXRecomp framework, with interpreter fallback. Campaign coverage remains incomplete, and movie playback is jittery.

The first gameplay feature is optional **1–4x normal battle EXP**, applied through guarded disc-read patches. See [EXP configuration and validation](docs/experience.md). Money is unchanged; an in-game settings entry remains planned. See the [progression formulas](docs/progression.md) and [menu/map groundwork](docs/menu-map.md).

See [Windows build, launch, and overlay-capture instructions](docs/windows-baseline.md) for the runnable baseline and current validation limits.

See the [groundwork audit and port milestones](docs/groundwork-audit.md) for pinned sources, verified findings, feature analysis, and reproduction commands.

## Planned work

- Expand EXP validation across party splits, later enemies and progression caps.
- Expand DV validation across later forms, participation splits and natural growth limits.
- Investigate music extraction and replacement instrument samples; compare a single track before expanding the work.
- Travel from visited map icons using X, with story and destination safeguards.
- In-menu random-encounter adjustment, including disabling random encounters while preserving scripted fights.

Fresh configurations retain original EXP until enabled. The current local setup selects 3x normal EXP and fixed 10-point DV awards.

## Local game data

Use a local disc dump as input. Keep the original unchanged; the EXP feature patches reads at runtime. Disc images, extracted assets, generated manifests and emulator saves are excluded from Git. This repository contains source, documentation and patch-generation logic rather than game data.

The current disc dump lives outside this repository, in a sibling directory. Future tooling should accept an explicit input path rather than depend on a machine-specific location.

See [investigation notes](docs/investigation.md) for findings and open questions.
