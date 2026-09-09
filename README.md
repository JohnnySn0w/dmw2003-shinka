# dmw2003-shinka

Mod development for Digimon World 2003, targeting the European multilingual PlayStation release (`SLES-03936`).

## Status

An experimental Windows x64 executable now builds and boots the supplied disc into language selection and the opening movie. Main-executable code and captured overlays compile locally through the pinned PSXRecomp framework, with interpreter fallback. Native savestate save/load works in the tested movie sequence. This is not yet a validated playable port: performance, exploration, battles, audible playback, and in-game saves still need testing. Gameplay mods are not enabled.

See [Windows build, launch, and overlay-capture instructions](docs/windows-baseline.md) for the runnable baseline and current validation limits.

See the [groundwork audit and port milestones](docs/groundwork-audit.md) for pinned sources, verified findings, feature analysis, and reproduction commands.

## Planned work

- Configurable 2–4× normal experience rewards to reduce grinding.
- Investigate separate Digivolution EXP scaling and its per-battle cap.
- Investigate music extraction and replacement instrument samples; compare a single track before expanding the work.
- Travel from visited map icons using X, with story and destination safeguards.
- In-menu random-encounter adjustment, including disabling random encounters while preserving scripted fights.

The exact default multipliers are not finalized. A 3× normal EXP / 3× Digivolution EXP preset is a proposed starting point.

## Local game data

Use a local disc dump as input. Keep the original unchanged and generate modified images separately. Disc images, extracted assets, and emulator saves are excluded from Git. This repository is intended to contain source, documentation, and patches rather than game data.

The current disc dump lives outside this repository, in a sibling directory. Future tooling should accept an explicit input path rather than depend on a machine-specific location.

See [investigation notes](docs/investigation.md) for findings and open questions.
