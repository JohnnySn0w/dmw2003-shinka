# dmw2003-shinka

Mod development for Digimon World 2003, targeting the European multilingual PlayStation release (`SLES-03936`).

## Status

Initial groundwork audit completed. Target: a Windows port with progressively reconstructed game systems and optional mechanics changes. The supplied disc has been identified and inspected, selected assets extracted locally, and the main executable translated to C using a locally built candidate recompiler. No playable Windows build or gameplay mods have been validated yet.

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
