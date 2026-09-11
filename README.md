<p align="center">
  <img src="assets/branding/shinka-title.png" alt="SHINKA — 進化" width="600">
</p>

<h1 align="center">Digimon World 2003 — Shinka</h1>

<p align="center">
  <a href="https://github.com/JohnnySn0w/dmw2003-shinka/actions/workflows/tests.yml"><img src="https://github.com/JohnnySn0w/dmw2003-shinka/actions/workflows/tests.yml/badge.svg?branch=main" alt="Python tests"></a>
  <a href="https://github.com/JohnnySn0w/dmw2003-shinka/actions/workflows/lint.yml"><img src="https://github.com/JohnnySn0w/dmw2003-shinka/actions/workflows/lint.yml/badge.svg?branch=main" alt="Python lint"></a>
  <a href="https://github.com/JohnnySn0w/dmw2003-shinka/actions/workflows/coverage.yml"><img src="https://github.com/JohnnySn0w/dmw2003-shinka/actions/workflows/coverage.yml/badge.svg?branch=main" alt="Python coverage report"></a>
  <a href="docs/windows-baseline.md"><img src="https://img.shields.io/badge/platform-Windows%20x64-0078D4" alt="Platform: Windows x64"></a>
  <a href="#status"><img src="https://img.shields.io/badge/status-experimental-orange" alt="Status: experimental"></a>
</p>

**Less grinding. More exploring. Keep the discovery.** Shinka is an experimental
Windows project for the European multilingual release of Digimon World 2003
(`SLES-03936`). It combines locally translated game code, a pinned PSXRecomp
runtime and interpreter fallback, with optional improvements to the original game.

## What changes?

| Feature | What you can do |
| --- | --- |
| [Portable Digimon Lab](docs/evolution-journal.md) | Choose battle forms, switch partners and load techniques from the field menu. Explore the evolution chart with directional hints for locked forms. |
| [Progression and encounters](docs/field-menu.md) | Select 1–4x normal/DV EXP or fixed 10-point DV awards, and random encounter rates from 0–200%. |
| [Live soundtrack switching](docs/music-live.md) | Switch between Original, DS, Sampled and Chip instruments mid-song. Alternate arrangements are provisional and use a locally built pack. |
| [Map travel](docs/menu-map.md) | Press X on eleven supported, visited Asuka-server destinations. Story checks protect the scenes audited so far. |
| [Screen view](docs/camera.md) | Choose battle widescreen, battle zoom and an experimental field widescreen preview. The field setting also widens gym/shop interfaces, both expanded Start-menu roots, Items, Sort and Techniques; remaining full-screen menus still use 4:3. |
| [Battle motion](docs/battle-animation-speed.md) | Adjust idle and action pose speeds separately, from 1–2x, while camera and script timing retain their own rates. |
| [Faster memory-card transfers](docs/save-timing.md) | Batch repeated file requests while preserving per-sector checks, flushes and completion handling. Existing card formats remain usable. |

See the [website source and gameplay showcase](website/README.md) for captures,
feature GIFs and an audible demonstration of all four soundtrack settings.
The [publishing guide](docs/website-publishing.md) covers GitHub Pages and custom domains.

## Build and play

Follow the [Windows build and launch guide](docs/windows-baseline.md). You need
Windows x64, the C++ build tools and your own supported disc data. The guide pins
the external framework and explains optional BIOS, overlay and native-unit builds.
This is not yet a standalone downloadable game package.

- [Enable the expanded menu and configure features](docs/field-menu.md).
- [Import a DuckStation memory card or choose a save profile](docs/save-profiles.md).
- [Keyboard and controller setup](docs/controller-support.md).
- [Browse the documentation](docs/README.md).

Fresh configurations retain original EXP and soundtrack settings until enabled.
Gameplay options are saved when changed through SETTINGS.

## Performance work

In matched local tests, the optional native battle-geometry unit used **31.4% less
process CPU time per frame** at an idle battle menu. The tested save body loaded
in **6.11 seconds instead of 25.02**, and an overwrite's file-sector writes
completed in **7.63 seconds instead of 28.72**. These are specific measurement
windows, not end-to-end load times or guarantees for every machine and scene.

The [profiling report](docs/performance.md) and [save timing investigation](docs/save-timing.md)
include methods, parity checks and limitations. Other work reduces redundant
movie scheduling, avoids a default 128 MiB debug history allocation, and
[pauses offline gameplay while minimized](docs/minimized-pause.md).

## Status

Tested gameplay includes early exploration, normal battles, shops, the gym,
memory-card saves/loads and savestates. **Campaign coverage remains incomplete.**
The English expanded menu, selected map destinations and individual checkpoints
have targeted validation; they do not establish full-game compatibility.

Field widescreen still has map-boundary and object-culling limitations. Longer
movie playback can stutter. Alternate soundtrack arrangements need listening
feedback. Controller coverage is limited. [Combat model smoothing](docs/combat-models.md)
is an offline prototype, not a higher-resolution in-game model replacement.

Next priorities include later-game progression and travel coverage, field
widescreen coverage, soundtrack balance and further measured optimization.

## Checks and contributions

The badges report the Python tooling's [tests, lint and coverage jobs](docs/testing.md).
Coverage percentages and per-file results live in the job summary and report;
the badge itself indicates job status. Synthetic Python tests do not require a
disc. Native regression tests and in-game validation are separate local checks.

For a bug report, include the build revision, scene, relevant settings and
reproduction steps. Keep saves and game data out of public issues. Developers
can use the [navigation tools](docs/developer-navigation.md) with copied profiles.

## Data and assets

Supply a local disc dump and keep the original unchanged. Disc images, BIOS
files, extracted resources, generated game code, music packs and saves stay
local and are excluded from Git. The repository contains source, documentation,
patch-generation logic, project branding and selected gameplay showcase media.
See [branding provenance](assets/README.md) and [showcase media notes](website/MEDIA.md).
