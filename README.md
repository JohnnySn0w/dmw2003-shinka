# dmw2003-shinka

Mod development for Digimon World 2003, targeting the European multilingual PlayStation release (`SLES-03936`).

## Status

An experimental Windows x64 build supports the tested early-game exploration, battles, shops, gym and saves. Main-executable code and captured overlays compile locally through the pinned PSXRecomp framework, with interpreter fallback. Campaign coverage remains incomplete, and movie playback is jittery.

The first gameplay feature is optional **1â€“4x normal battle EXP**, applied through guarded disc-read patches. See [EXP configuration and validation](docs/experience.md). Money is unchanged; the expanded field menu now includes live EXP settings. See the [progression formulas](docs/progression.md) and [menu/map groundwork](docs/menu-map.md).

An experimental English menu adds **DIGIVOLUTIONS** and **SETTINGS** as selectable rows in both the world overlay and the full-screen root reached after leaving a submenu. Enable it with `python tools/configure_journal.py --enable` and restart. DIGIVOLUTIONS opens the full lab interface for switching partners, selecting battle forms, loading techniques and viewing the chart; leaving it highlights DIGIVOLUTIONS again. Select an anonymous chart node and press X for directional training hints. SETTINGS includes live EXP controls and **0%, 50%, 100%, 150%, 200% random encounter rates**. See [menu controls and implementation](docs/field-menu.md), [encounter behavior](docs/encounters.md) and [lab integration](docs/evolution-journal.md).

See [Windows build, launch, and overlay-capture instructions](docs/windows-baseline.md) for the runnable baseline and current validation limits.

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

The [developer navigation tool](docs/developer-navigation.md) provides named
warps, position bookmarks, measured movement, routes and checkpoints, plus
explicit story/quest and HP/MP/strength edits for testing in copied profiles.

See the [groundwork audit and port milestones](docs/groundwork-audit.md) for pinned sources, verified findings, feature analysis, and reproduction commands.

The [offline music exporter](docs/music.md) converts owned BGM packs into MIDI,
sample WAVs with loop points, and instrument metadata. All 30 BGM pairs export
successfully. [Offline soundtrack auditions](docs/music-palettes.md) render
BGM001 with CC0 sampled instruments, a 24-voice oscillator-chip palette, or the
preferred **DS-inspired hybrid** of samples and synth accents.
Runtime music replacement remains pending.

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
