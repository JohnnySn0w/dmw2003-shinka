# Documentation

Start with the [project overview](../README.md) or the [Windows build and launch guide](windows-baseline.md).
Feature pages describe current behavior and its validation limits. Dated audit
sections preserve earlier observations; they are not all current limitations.

## Playing and configuring

| Topic | Guide |
| --- | --- |
| Installation and launch | [Windows baseline](windows-baseline.md) |
| Existing memory cards | [Save imports and profiles](save-profiles.md) |
| Buttons and devices | [Controller compatibility](controller-support.md) |
| Menu settings | [Expanded field menu](field-menu.md) |
| Forms, techniques and hints | [Portable Digimon Lab](evolution-journal.md) |
| EXP and DV growth | [Configuration](experience.md), [progression formulas](progression.md) |
| Random fights | [Encounter rates](encounters.md) |
| Fast travel | [Destinations and story checks](menu-map.md) |
| Aspect ratio and zoom | [Camera and screen view](camera.md) |
| Animation speed | [Battle motion](battle-animation-speed.md) |
| Soundtrack choices | [Live switching](music-live.md), [per-track listening guide](music-listening-guide.md) |

## Performance and compatibility evidence

- [Runtime profiling](performance.md): measured CPU and memory work, including battle geometry and movies.
- [Save timing](save-timing.md): read/write batching, matched data and failure checks.
- [Minimized-window pause](minimized-pause.md): suspension and resume behavior.
- [Runtime timing map](runtime-timing-map.md): scheduler, CD, movie and audio relationships.
- [Partner-selection exit](partner-selection-exit.md): overlay validation and the original crash.
- [Testing](testing.md): what CI, native tests and gameplay checks each cover.

## Development and research

- [Groundwork audit](groundwork-audit.md) and [investigation notes](investigation.md): pinned sources and the port's research history.
- [Developer navigation](developer-navigation.md): routes, checkpoints and diagnostic edits in copied profiles.
- [Host stack profiling](host-stack-profiling.md): finding costly runtime paths.
- [Music format/export](music.md) and [palette design](music-palettes.md): local soundtrack tooling.
- [Combat models](combat-models.md): format analysis, export and offline smoothing prototype.
- [Title screen](title-screen.md) and [branding](../assets/README.md): project artwork integration.
- [Website](../website/README.md) and [media provenance](../website/MEDIA.md): the feature showcase.
