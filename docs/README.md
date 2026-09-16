# Documentation

Start with the [project overview](../README.md) or the [Windows build and launch guide](windows-baseline.md).
Feature pages describe current behavior and its validation limits. Dated audit
sections preserve earlier observations; they are not all current limitations.

For a new checkout, build using your own supported disc, launch through the
PowerShell helper, and enable `-EvolutionJournal` if you want DIGIVOLUTIONS and
SETTINGS. Use a separate save profile when copying a DuckStation card. The
maintainer's existing executable settings, soundtrack pack and shortcuts are
local files, not prerequisites already supplied by cloning the repository.

## Current feature guide

The player-facing summaries below reflect the September 15, 2026 updates:

- **Travel:** 15 exact arrival fields, including South Badland and Bullet Valley.
  Visitation, source-area support and story checks all apply. Noise Desert is
  still under event audit; visibility on the map does not imply travel support.
- **Menus:** widescreen adjustments cover supported Status, card and Lab screens,
  including selection pulses and page turns. See the scene matrix rather than
  treating an older audit's 4:3 observation as the current rule.
- **Saving:** read/write batching plus a transfer-driven save/load bar. The
  measured sector timings are not total menu-to-world waits.
- **Controls:** L2/LT toggles aspect ratio; R2/RT toggles speedup. Keyboard and
  gamepad button labels are mapped explicitly in the controller guide.
- **Music:** all four live palettes remain available; per-track balance is
  provisional. The instrument notebook saves listening labels locally without
  automatically changing the game's instrument routes.

## Playing and configuring

| Topic | Guide |
| --- | --- |
| Installation and launch | [Windows baseline](windows-baseline.md) |
| Existing memory cards and file locations | [Save imports and profiles](save-profiles.md) |
| Buttons and devices | [Controller compatibility](controller-support.md) |
| Menu settings | [Expanded field menu](field-menu.md) |
| Forms, techniques and hints | [Portable Digimon Lab](evolution-journal.md) |
| EXP and DV growth | [Configuration](experience.md), [progression formulas](progression.md) |
| Random fights | [Encounter rates](encounters.md) |
| Fast travel | [Destinations and story checks](menu-map.md) |
| Aspect ratio and zoom | [Current screen coverage](camera.md#current-screen-coverage), [camera settings](camera.md) |
| Animation speed | [Battle motion](battle-animation-speed.md) |
| Soundtrack choices | [Live switching](music-live.md), [per-track listening guide](music-listening-guide.md) |
| Identify instruments by ear | [Instrument labeling notebook](music-live.md#instrument-labeling-notebook) |

## Performance and compatibility evidence

- [Runtime profiling](performance.md): measured CPU and memory work, including battle geometry and movies.
- [Save timing](save-timing.md): read/write batching, transfer-driven progress, matched data and failure checks.
- [Minimized-window pause](minimized-pause.md): suspension and resume behavior.
- [Runtime timing map](runtime-timing-map.md): scheduler, CD, movie and audio relationships.
- [Partner-selection exit](partner-selection-exit.md): overlay validation and the original crash.
- [Testing](testing.md): what CI, native tests and gameplay checks each cover.

## Development and research

- [Groundwork audit](groundwork-audit.md) and [investigation notes](investigation.md): pinned sources and the port's research history.
- [Developer navigation](developer-navigation.md): routes, checkpoints and diagnostic edits in copied profiles.
- [Travel story audit](travel-story-audit.md): original event predicates, tested entrances and remaining campaign coverage.
- [Host stack profiling](host-stack-profiling.md): finding costly runtime paths.
- [Music format/export](music.md) and [palette design](music-palettes.md): local soundtrack tooling.
- [Combat models](combat-models.md): format analysis, export and offline smoothing prototype.
- [Title screen](title-screen.md) and [branding](../assets/README.md): project artwork integration.
- [Website](../website/README.md), [publishing and domains](website-publishing.md) and [media provenance](../website/MEDIA.md): the feature showcase.

## Reading the evidence

Implementation notes explain what the code does; native regressions exercise
specific rules; copied-save replays check selected gameplay paths. A developer
warp is not a naturally earned arrival, and a synthetic story-flag fixture is
not a complete campaign playthrough. Dated test counts describe the run recorded
there. Use [testing](testing.md) for current commands and coverage boundaries.

Links into `output/`, `extracted/` or `build-windows/` identify local artifacts.
They are intentionally absent from GitHub and a fresh clone. Public screenshots
and the short soundtrack demonstration are under `website/dist/media/`.
