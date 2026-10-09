# Windows installer and first-run setup

Status: local installer prototype built October 8, 2026; not publicly released.
The user requested a setup experience requiring only their own supported disc
dump, with installer behavior discussed before implementation. The public
[getting-started page](../website/dist/get-started.html) distinguishes this plan
from the existing source-build route. The implementation now lives in
`tools/shinka_launcher.py`, `tools/setup_core.py`, `tools/setup_prepare.py`,
`tools/package_setup_sdk.py`, `tools/build_installer.py` and `packaging/shinka.iss`.

## Implemented prototype

- Per-user Inno Setup package, with Play and Setup Start-menu shortcuts and an
  optional desktop shortcut. Uninstall retains `%LOCALAPPDATA%/Shinka`.
- Frozen Python/Tk launcher; players do not install Python, Visual Studio, SDL or
  separate compiler DLLs. Setup downloads a SHA-256-pinned 200 MiB portable
  LLVM-MinGW/UCRT toolchain. The generated game imports only Windows system DLLs.
- Local preparation from the checked European single-BIN CUE, using included
  OpenBIOS. The SDK contains allowlisted source and authored assets; generated
  game code and extracted data stay on the player's machine.
- Battle/movie native units are generated directly from the player's disc.
  Other overlays use interpreter fallback; a maintainer capture archive is not
  required. This is not the same native-overlay coverage as the development build.
- Opt-in DuckStation search, redirected Documents support, custom folder/card
  pickers, explicit card selection, and verified copies into new save profiles.
- Named preparation stages, cancellation, resumable completed extraction, 6 GiB
  free-space check, duplicate-instance lock, atomic activation, disc relocation
  repair, and retained previous runtime/profile during updates.
- Original soundtrack initially; alternate music preparation remains separate.
  The expanded menu is enabled, with original progression/view defaults.

Local validation at implementation revision `2397080`:

- A second, fresh SDK preparation completed without source edits or a toolchain
  override. It verified/unpacked the cached official toolchain archive and built
  all conversion tools and the game with host development tools excluded from PATH.
- OpenBIOS played the intro, reached the title/Continue menus, loaded a verified
  copy of a DuckStation card, reached Pelche Oasis and opened the expanded menu.
- The frozen launcher and optional save-search controls were inspected. The
  installed Play button launched the final build with only Windows directories
  on PATH and passed the selected save-profile path explicitly.
- Installation and uninstallation succeeded in a dedicated test directory.
  After uninstall, the separate launcher settings remained and the selected
  memory card's SHA-256 was unchanged.
- 223 Python tests passed, including 14 new setup tests; Ruff passed. The existing
  MSVC game build and native view, overlay-guard and title-logo checks passed.
- PE import inspection found only Windows system DLLs in the prepared game.

Local artifact: `output/installer-20261008/final/package/release/` contains
`Shinka-Setup-0.1.0-preview-windows-x64.exe` (21,141,873 bytes), with SHA-256
`f9d541165f0d5804aef31d0cefbc17d9404f424060bdc8c8b9a8164828344845`.
The source SDK SHA-256 is
`5adc4195b142454679a3dccf8be6dd53fe243386c50375cecda9a30e730c681d`.
Evidence, copied profiles and logs remain local under `output/installer-20261008/`.

### October 8: cold save roundtrip and Unicode paths

The installer-built OpenBIOS runtime loaded an isolated copy of the imported
Pelche Oasis card, entered Guardromon's save screen through ordinary movement
and dialogue, overwrote that disposable slot and displayed Saved. After a full
process exit, a fresh process loaded the newly written file through Continue and
returned to Pelche Oasis with the same story and party. The card hash changed
on saving and remained identical across the cold reload. The original imported
card and the player's source card were not used as writable targets.

A separate runtime/profile copy under `José 進化` exposed a launch failure:
the existing `game.toml` was reported missing. The runtime now embeds a
per-process UTF-8 manifest, and that same path reaches the field through Continue.
The conversion tools receive the same manifest during setup. This uses the
[Windows per-process code-page declaration](https://learn.microsoft.com/en-us/windows/apps/design/globalizing/use-utf8-code-page),
without changing system locale. Setup requires Windows 10 1903 or later.
An executable regression exercises Unicode command-line arguments, C++ file
reads and C-style file writes with both MSVC and the portable Clang toolchain.
Evidence stays under `output/installer-20261008/roundtrip/` and `unicode/`.

The original preview artifact above predates the Unicode fixes. A refreshed
`0.1.1-preview` uses source revision `40d6962` and completed fresh preparation
under `output/setup-final-é進` using the previously verified portable toolchain.
No staged source edits were needed. The first extraction attempt encountered a
Windows access-denied error renaming its staging directory; retrying completed
the entire preparation. This retry used a new extraction directory.

The refreshed installer also installed successfully into `installed-é進`. Its
installed launcher starts the freshly prepared game with only Windows folders
on PATH and a copied save profile under `José 進化`. Continue read the new
59:53:06 save and reached Pelche Oasis's area load-in (stage `0x249`, story 20);
both card hashes remained unchanged during loading. Uninstalling this test
installation succeeded and retained the separate settings and save profile.

Local artifact: `output/installer-20261008/release2/package/release/` contains
`Shinka-Setup-0.1.1-preview-windows-x64.exe` (21,156,667 bytes), with SHA-256
`1e81b3d46528e5d31f3e2d854268436fbed09ef315cce6c02772876253a4350e`.
The source SDK SHA-256 is
`c60cc7544d416b7a5cfcdb4424285c63908e807116679e284ae13adce4847ed1`.
The 15 focused setup tests pass. Build, installation and launch evidence remains
local under `output/installer-20261008/release2/` and `output/setup-final-é進/`.

The full release checks below still apply. A fresh Windows VM, reboot/reinstall
and a new-game-to-battle flow remain outstanding. The preview is unsigned and
has not been uploaded as a public release.

### Building a local installer

Use a packaging venv with `PyInstaller==6.16.0`, the pinned source dependencies
from the Windows build guide, and an Inno Setup compiler (tested with 7.1.0).
Commit source changes before packaging so the SDK revision identifies its inputs.

```powershell
python tools/package_setup_sdk.py --candidate 'PATH\TO\dmw2003' --output output/setup/sdk.zip
python tools/build_installer.py --sdk output/setup/sdk.zip --output output/setup/package --iscc 'PATH\TO\ISCC.exe' --version 0.1.0
```

The result and SHA-256 file are under `output/setup/package/release/`. Build
outputs are ignored and must not be committed. A maintainer can test isolated
settings with `Shinka.exe --settings --data 'PATH\TO\test-data'`; normal players
use the installed shortcuts. Preparation logs live inside each data-folder
`builds/<version>/` directory, and game logs under `logs/`.

## Player experience

1. Run the Windows installer. Install for the current account and add a Start-menu
   shortcut; offer a desktop shortcut. Do not change file associations or add a
   startup service.
2. Use a Windows file picker to select the game's CUE at its existing location.
   Remember that absolute path for later launches. Resolve its BIN references and check readable files,
   supported structure, disc identity and the existing audited hash. Explain
   wrong region, missing BIN, unsupported format and unreadable file separately.
   Keep the original dump unchanged.
3. Show required download and disk space before starting preparation. Perform
   local extraction and game preparation automatically, with named stages,
   progress where measurable, cancellation and retry. Do not present an invented
   percentage for compilation or waiting on external tools.
4. Offer Start fresh or Import a memory card. Include an initially unchecked
   **Search for existing emulator data** checkbox. When selected, search common
   DuckStation data locations and provide **Choose folder…** for custom or
   portable installations. Show discovered cards for the player to select; copy
   and verify a raw 128 KiB MCD using the existing import rules. Never overwrite
   another profile or modify the source. Explain that DuckStation savestates are
   a different format.
5. Show Ready to play, a Play button, Open saves folder and controller check.
   Subsequent launches go straight to the game unless setup needs repair.

Recommended defaults: enable the expanded menu; keep original EXP, encounters,
music and view settings until the player changes them. Offer optional widescreen
in setup. Alternate music must not delay the first successful launch; make its
local preparation an optional later step, with its own progress and recovery.

## Disc storage decision

User decision, October 1: **use the original files in place**. Provide a Windows
file picker so players select the path instead of typing or editing settings.
Persist the validated path and show it in launcher settings with a Change button.
Do not copy the disc into application storage. If the dump moves or its drive is
disconnected, offer Locate disc and Retry without losing settings or saves.

Resolve all inputs before installing modifications. Handle
spaces, apostrophes, non-ASCII names and long paths. Treat a CUE as untrusted
input: validate references, never execute it, never silently fetch missing files,
and show the resolved files before preparation. Stage writes and verify hashes before
committing a usable profile; cancellation must not destroy prior working data.

## Installation and updates

### Existing emulator discovery

User decision, October 1: opt-in discovery with a folder-picker fallback.
Implement DuckStation support first; do not imply every emulator is supported.

- Only start discovery when the checkbox is selected. Search known user data
  locations, including a redirected Documents folder where applicable. Read
  DuckStation's configuration to resolve its configured memory-card directory
  when available. Confirm exact supported layouts during implementation.
- **Choose folder…** accepts a custom DuckStation data/portable-install folder
  or a memory-card folder. Explain what to select. Keep discovery bounded to
  known subdirectories and configured card locations; do not scan entire drives.
- List candidate cards with filename, source location, size and modification
  date. Show game/save labels only when reliably parsed. Do not pick a card solely
  because its name looks like this game, and do not infer play progress from dates.
- Validate format before import, distinguish slot 1/2 and game-specific cards,
  and deduplicate the same resolved source path. An emulator installation alone
  does not mean a usable memory card exists.
- If no cards are found, offer Choose folder, Choose card file or Start fresh.
  Explain unreadable locations without treating them as an empty successful scan.
- Require the source emulator to be closed before copying, verify the source
  remains unchanged across import, and retain existing exclusive-create behavior.
  Never point Shinka's writable card path at DuckStation's live card.
- Remember only the imported Shinka profile for play. Unchecking discovery or
  cancelling the picker must not create, import or delete anything.

### Application storage

Prototype installer locations (the source-build layout remains separate):

- Application files: `%LOCALAPPDATA%/Programs/Shinka`.
- Writable data: `%LOCALAPPDATA%/Shinka`, with separate generated-data,
  settings, cache, logs, backups and save-profile directories.
- Launch through a stable setup/launcher entry point, passing validated absolute
  paths and an explicit working directory to the runtime. Do not rely on where a
  shortcut happens to start.
- Keep disc data, saves and preferences through upgrades. Stage and validate an
  update before switching the active version; retain the last working version.
- Uninstall application files while preserving player data by default. Removal
  of saves requires a distinct, explicit choice.
- Provide Locate disc, Open saves folder and a readable error with a retry action.
  Diagnostics should be opt-in exports with personal paths redacted; no automatic
  upload of disc data, memory cards or logs.

The runtime currently writes some settings beside the executable and shares
`mods/state.toml` across save profiles. Either relocate those stores or make their
ownership explicit before packaging; an installer cannot simply change folder
names and assume persistence still works.

## Remaining release checks

The portable toolchain, source-only SDK, setup/repair launcher and per-user
installer are implemented. They replace the developer prerequisites for the
installer route; the source-build instructions remain available separately.

Before publishing a download:

- Complete a fresh OpenBIOS new-game-to-battle run. Imported-card loading and
  an in-game save/full restart/Continue cycle already pass; earlier battle
  coverage used the optional retail BIOS backend.
- Test in a clean Windows x64 environment without developer tools or maintainer
  paths, using a standard user account. Reboot, reinstall and check the installed
  shortcut with retained settings and cards.
- Exercise missing/incorrect dumps, relocated discs, interrupted downloads and
  builds, low disk space and update recovery through the packaged UI. Unit tests
  cover several of these cases; they do not replace the installed-app checks.
- Broaden DuckStation discovery checks: no installation, redirected and custom
  folders, external card paths, duplicate candidates, denied access and a card
  changing during import.
- Decide signing and publish the exact version, integrity hashes, supported
  Windows versions and notices. The installer currently targets Windows 10 1903
  or later, x64.

Keep game-derived code/assets, retail BIOS, music packs and player saves outside
public release inputs. Package only the explicit source allowlist. The prepared
runtime has battle/movie native units and interpreter fallback elsewhere; do not
promise the development build's complete native-overlay coverage.

Only add a download button when the release checks pass. Until then, describe
the installer as in local testing and retain the source-build guide.
