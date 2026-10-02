# Windows installer and first-run setup

Status: proposed, October 1, 2026. No installer has been built or released.
The user requested a setup experience requiring only their own supported disc
dump, with installer behavior discussed before implementation. The public
[getting-started page](../website/dist/get-started.html) distinguishes this plan
from the existing source-build route.

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

Proposed locations, not the current runtime layout:

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

## Work required before a downloadable installer

### 1. Prove disc-only boot

The default source build includes OpenBIOS. Existing evidence only confirms it
through language selection. The more complete movie, gameplay and savestate
checks used the optional SCPH-1001 backend. Validate a clean OpenBIOS run through
new game, field, battle, in-game save, full restart and Continue. Fix failures
before claiming the player's disc dump is the only input needed.

### 2. Make local preparation self-contained

`tools/build_windows.ps1` currently needs Visual Studio 2022 C++/Windows SDK,
CMake, Git and Python. It builds a recompiler, generates local game code and then
builds the runtime. The optional optimized build additionally uses local overlay
captures. `CMakeLists.txt` explicitly rejects a build without generated game code.

Select and validate a redistributable preparation toolchain or an alternative
runtime/package design. A player should not need to choose compiler components,
edit PATH or open a developer terminal. Do not quietly install Visual Studio as
an undocumented substitute for this requirement. Account for licenses, notices,
download size, disk space, supported Windows versions and offline retries when
selecting the packaging approach.

Keep generated game code, extracted assets, retail BIOS, local music packs and
player saves outside public release inputs, consistent with current repository
boundaries. Build the release from an explicit allowlist, never by archiving the
maintainer's working runtime directory. The current optimized development build
must not be promised as the fresh-install build until it is reproducible from
the player's disc without private fixtures.

### 3. Implement setup and repair

Add a startup entry point that validates inputs before initializing disc-dependent
mods. Persist paths atomically, preserve unrelated preferences and show the chosen
save profile. Add backup/import, disk-space checks, interrupted-setup recovery
and duplicate-instance handling. Package the launcher and authored resources
with a normal Windows installer. Choose the installer technology only after the
payload and preparation strategy are proven.

### 4. Release checks

Validate in a clean Windows x64 environment without developer tools or maintainer
paths. Cover a standard user account, fresh install, existing-save import,
non-ASCII paths, missing/incorrect dump, low disk space, interrupted setup,
relocated disc, update rollback and uninstall/reinstall with retained saves.
Exercise discovery with no DuckStation installation, default and redirected user
folders, portable/custom folders, configured external card paths, duplicate
candidates, invalid cards, denied access and a card changing during import.
Confirm the shortcut launches the selected profile after a reboot. Include a
signing/reputation plan and publish exact version, integrity hashes, supported
Windows versions and notices with the installer.

Only add an installer download button after that artifact exists and has passed
these checks. Until then, the website should call it planned and keep the current
source-build guide available.
