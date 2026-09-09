# dmw2003-shinka

Mod development for Digimon World 2003, targeting the European multilingual PlayStation release (`SLES-03936`).

## Status

An experimental Windows x64 build supports the tested early-game exploration, battles, shops, gym and saves. Main-executable code and captured overlays compile locally through the pinned PSXRecomp framework, with interpreter fallback. Campaign coverage remains incomplete, and movie playback is jittery.

The first gameplay feature is optional **1â€“4x normal battle EXP**, applied through guarded disc-read patches. See [EXP configuration and validation](docs/experience.md). Money is unchanged; the expanded field menu now includes live EXP settings. See the [progression formulas](docs/progression.md) and [menu/map groundwork](docs/menu-map.md).

An experimental English menu adds **DIGIVOLUTIONS** and **SETTINGS** as selectable rows in both the world overlay and the full-screen root reached after leaving a submenu. Enable it with `python tools/configure_journal.py --enable` and restart. DIGIVOLUTIONS opens the full lab interface for switching partners, selecting battle forms, loading techniques and viewing the chart; leaving it highlights DIGIVOLUTIONS again. Select an anonymous chart node and press X for directional training hints. See [menu controls and implementation](docs/field-menu.md) and [lab integration](docs/evolution-journal.md).

See [Windows build, launch, and overlay-capture instructions](docs/windows-baseline.md) for the runnable baseline and current validation limits.

Existing DuckStation memory cards can be copied into isolated test profiles; see [save imports and profile selection](docs/save-profiles.md).

See the [groundwork audit and port milestones](docs/groundwork-audit.md) for pinned sources, verified findings, feature analysis, and reproduction commands.

## Planned work

- Expand EXP validation across party splits, later enemies and progression caps.
- Expand DV validation across later forms, participation splits and natural growth limits.
- Investigate music extraction and replacement instrument samples; compare a single track before expanding the work.
- Add directional hints and selected-partner retention to the DIGIVOLUTIONS entry; see [design and hint groundwork](docs/evolution-journal.md).
- Travel from visited map icons using X, with story and destination safeguards.
- In-menu random-encounter adjustment, including disabling random encounters while preserving scripted fights.

Fresh configurations retain original EXP until enabled. The current local setup selects 3x normal EXP and fixed 10-point DV awards.

## Local game data

Use a local disc dump as input. Keep the original unchanged; the EXP feature patches reads at runtime. Disc images, extracted assets, generated manifests and emulator saves are excluded from Git. This repository contains source, documentation and patch-generation logic rather than game data.

The current disc dump lives outside this repository, in a sibling directory. Future tooling should accept an explicit input path rather than depend on a machine-specific location.

See [investigation notes](docs/investigation.md) for findings and open questions.
