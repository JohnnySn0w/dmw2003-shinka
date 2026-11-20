# Windows installer and first-run setup

Status: [0.1.5-preview published November 19, 2026](https://github.com/JohnnySn0w/dmw2003-shinka/releases/tag/v0.1.5-preview).
Both public assets were downloaded and verified against the local installer and checksum.
The user requested a setup experience requiring only their own supported disc
dump, with installer behavior discussed before implementation. The public
[getting-started page](../website/dist/get-started.html) distinguishes this plan
from the existing source-build route. The implementation now lives in
`tools/shinka_launcher.py`, `tools/setup_core.py`, `tools/setup_prepare.py`,
`tools/package_setup_sdk.py`, `tools/build_installer.py` and `packaging/shinka.iss`.

## Current preview: 0.1.5 (November 19)

Launcher-only branding refresh: the full SHINKA title artwork replaces the plain
text heading, with no subtitle. The image is bundled with the frozen launcher;
the expanded import controls fit the existing 780-pixel window height. This
reuses the validated game SDK from 0.1.4; game preparation is unchanged.

Local installer:
`output/installer-logo-20261119/package/release/Shinka-Setup-0.1.5-preview-windows-x64.exe`
(21,511,404 bytes). SHA-256:
`341ca41ebb5d26bae79afd0d63a6d9079a7c4933f2f2e39ae46a84e44138c026`.

### Preview recovery checks (November 19)

The release scope is recovery checks followed by an unsigned Windows preview.
Clean-Windows/reboot testing, broader DuckStation discovery/import coverage and
alternate soundtrack setup are deferred at the user's request; they are not
gates for this preview. These limits must remain visible in the release notes.

- All 26 focused setup tests pass. New fault-injection cases cover a connection
  reset, truncated download, incorrect checksum and oversized download. Every
  case rejects the input, removes the partial download, preserves active data
  and successfully retries with a verified archive.
- An actual failed subprocess reports its preparation stage and can retry.
  Cancelling a running subprocess waits for it to exit. This new check covers
  the direct build process, not every possible compiler descendant.
- A simulated failed atomic activation preserves the active configuration,
  preferences and card bytes; a subsequent successful activation retains the
  same profile and preferences.
- The tested `setup_core.py` and `setup_prepare.py` match the bundled source SDK
  byte for byte. No launcher/runtime fix or replacement installer was needed.
  The installer SHA-256 was rechecked against the value above.
- The complete Python suite passes (260 tests), and Ruff passes for tools/tests.
  Local test output: `output/installer-logo-20261119/recovery-tests.log`.

These automated checks complement the packaged missing-BIN/retry test and
install/reinstall/uninstall checks below. They are not a claim that every failure
was reproduced through the installed UI. The user's GitHub release draft uses
tag `v0.1.5-preview`; attach the installer and its matching `.sha256` file.

### 0.1.4 preparation and installer validation

Refreshed from game revision `1c1a41a`, including the widened field visibility
fixes and new 125% idle / 200% action animation defaults. The local package is
`output/installer-20261119/package/release/Shinka-Setup-0.1.4-preview-windows-x64.exe`
(21,165,618 bytes). SHA-256:
`195ee62085b4077c50218a90bb893bd7cc1f8a722f524f6ad5bb4c1f4260cedf`.
Source SDK SHA-256:
`c87c0fee345e0f989594dff89cc29e4f2fbf8187d7857af39a8c21e8e7026ce0`.

- Fresh preparation succeeded using only the pinned portable toolchain and
  Windows directories on PATH. The previously downloaded official archive was
  hash-checked and unpacked into a fresh data directory; no toolchain override
  or staged source edits were used. This was a local test, **not a clean VM**.
- The installer installed, reinstalled and uninstalled in a dedicated test
  directory. All three returned success. The separate launcher settings and
  imported test card retained their exact SHA-256 hashes after uninstall.
- The installed frozen launcher's first-run screen and cancelled disc picker
  were inspected. Its prepared-profile Play button launched the new runtime
  with Windows-only PATH. PE imports contain only Windows system libraries.
- Ten source Tk recovery checks passed: missing runtime components, relocated
  disc repair, missing/restored save folders and fresh setup. These are fixture
  checks, not a substitute for the complete packaged failure/recovery matrix.
- A separate frozen-launcher check rejected a CUE referencing a missing BIN,
  disabled Play and displayed the missing filename with recovery guidance.
  The failed attempt preserved settings and card hashes. After repairing that
  test CUE's reference, Save setup returned to Ready to play with the same
  runtime, save profile and unchanged card. This tested retry, not the file picker.
- Installer path assertions now compare the actual `--disc` argument as a path,
  preserving Windows case-insensitive semantics. The earlier literal-string
  checks falsely rejected differently capitalized names of the same directory.
- All 256 Python tests and Ruff passed, including guarded startup automation.
  A fresh process reached the load screen with the scripted delays, read the
  copied 59:53:06 card save and returned to Pelche Oasis (`0x249`, story 20).
  This pass tested loading, not a new save/write roundtrip.

Logs, hashes and copied profiles remain under `output/installer-20261119/`.
Use the repeatable [startup command](developer-navigation.md#repeatable-startup-with-an-imported-card)
for later installer smoke checks rather than manually timing the two Start presses.

Additional coverage remains outside this preview: a clean Windows standard-user
machine and reboot, the full packaged failure/recovery matrix, and broader save
discovery/import cases. This release is intentionally unsigned.
The apparent missing title logo was a capture error:
raw `screenshot_file` images exclude the host-drawn artwork. A `present_shot`
capture of this same prepared runtime confirms the logo displays correctly;
no renderer or installer change was needed. Startup evidence now uses that API.
No Windows Sandbox, Hyper-V, VirtualBox, VMware or
QEMU environment was available during this pass. The preview remains unsigned
in this first public release; the source-build route remains available separately.

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

The full release checks below still apply. A fresh Windows VM and reboot/reinstall
remain outstanding. The preview is unsigned and has not been uploaded as a
public release.

### October 9: fresh OpenBIOS game through the first battle

The runtime prepared from SDK revision `40d6962` started with a separate empty
memory-card directory and only Windows directories on PATH. Its log confirms
OpenBIOS and creation of two blank cards. No imported card, savestate restore,
warp, story edit, stat cheat or encounter override was used during this run.

Normal controller inputs progressed through the street opening, account/name
registration, Balanced Pack selection, login movie, Digital World arrival and
the upstairs partner-service interaction. Kotemon, Renamon and Patamon appeared,
and the story triggered Tamer Genji's tutorial battle outside the lobby.

The battle loaded Kuwagamon and Kotemon, accepted the Tech command and Hot Head,
displayed 165 damage and defeated Kuwagamon. The results screen awarded Kotemon
4 EXP and 50 BIT, then returned to Genji's post-battle dialogue in Asuka City
(field `0x200`, story 3). This covers the first scripted battle; broader random
encounters, partner changes and late-game combat on OpenBIOS remain separate
checks. It does not substitute for clean-machine or sustained-performance testing.

Screenshots, state records, launcher inputs and the boot log remain local under
`output/installer-20261009/new-game/`. In particular, `battle-tech.png`,
`battle-result.png`, `victory-ready.png`, `rewards-applied.png` and
`battle-return.png` record command selection, damage, rewards and field return.
A diagnostic checkpoint was created in slot 0 after this run for later checks;
it was not restored during validation.

### October 9: preparation recovery

Source/toolchain staging now retries Windows access-denied and sharing-lock
rename failures up to five attempts, with at most three seconds of cancellable
backoff. Other errors return immediately; permanent locks still report an error
and retain the staging data. This addresses the transient extraction failure
seen during the Unicode preparation check without retrying indefinitely.

Malformed or mismatched tool-cache markers now trigger verified re-extraction
instead of preventing Retry. The cache check also requires the C++ compiler.
An invalid prior tool directory is retained separately after successful
extraction; it is never merged into the replacement.

Twenty focused setup tests pass, including transient/permanent locks,
cancellation during the retry wait and download, repair from a verified cached
archive, and disc relocation preserving the runtime, save profile and card
bytes. A separate Windows process test confirmed Cancel terminates both a
disposable worker and its child. Its evidence is local under
`output/installer-20261009/recovery/`. These checks cover the recovery code;
the packaged-UI failure matrix and clean-machine tests below remain outstanding.

The source-only SDK and local installer were rebuilt at revision `c298664`.
`output/installer-20261009/recovery/package/release/` contains
`Shinka-Setup-0.1.2-preview-windows-x64.exe` (21,158,004 bytes), SHA-256
`d1bd16f19dfa19180de8a56290eb220c8fa15d1c3b46c40c571160909fa3fb95`.
SDK SHA-256:
`7ddbdcb5b62e7f4e41fd319a9df892e47d1e3d34c3fe1ec7d2c8b8526c1cf8c6`.
This preview includes the recovery changes; the earlier full preparation and
gameplay results identify their respective tested revisions above. No new
public installer download has been published.

### October 17: incomplete installations and launcher recovery

Readiness now checks the executable, game configuration, OpenBIOS and extracted
game executable together. Missing inputs disable Play and show **Repair Shinka**;
a moved disc shows the CUE-selection recovery steps, and a missing save folder
asks for restoration instead of reporting that the installation is ready.
Automatic launch and manual Play use the same checks.

Repair skips incomplete builds previously marked ready and stages a separate
replacement. It does not reuse their source directory or overwrite the active
runtime during preparation. Activation rejects incomplete replacements before
copying preferences or changing the remembered installation.

All 240 Python tests pass, including 23 setup tests. Ten local checks against the
actual Tk widgets cover fresh setup, ready state, each missing launch input,
disc relocation, missing/restored save folders, and the threaded Save setup
callback. Relocation preserved the runtime, profile and card bytes. Disposable
fixtures were used; this was not a new full disc preparation or clean Windows VM
test. Evidence: `output/installer-recovery-20261017/ui-results.json` and
`output/installer-recovery-tests-20261017.log`. Packaged failure-path testing and
the release checks below remain open.

Local preview `0.1.3-preview` packages source revision `323e670`. The frozen
launcher was opened with isolated missing-runtime settings: the repair message,
**Repair Shinka** action and disabled Play button rendered correctly. This was
a packaged-launcher smoke check, not an install/uninstall or full repair run.
Artifact: `output/installer-recovery-20261017/package/release/`
`Shinka-Setup-0.1.3-preview-windows-x64.exe` (21,160,808 bytes).
Installer SHA-256:
`a30179bb58cfb6014b1a38a867454ec0fdccda4e5c156277d55ff690a0b043f8`.
SDK SHA-256:
`7abaff6ecab671d460abfe7cf551c595ff9891fa6241daa61cf436651c479e53`.
The installer remains local; no public download was added.

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

## Preview release checklist

The portable toolchain, source-only SDK, setup/repair launcher and per-user
installer are implemented. They replace the developer prerequisites for the
installer route; the source-build instructions remain available separately.

- [x] Verify recovery behavior and record automated versus packaged coverage.
- [x] Recheck the release artifact's integrity hash and matching preparation code.
- [x] Choose an unsigned preview with explicit limitations.
- [x] Draft `v0.1.5-preview` on GitHub (user confirmed).
- [x] Publish the draft with the installer and checksum attached.
- [x] Verify the public download, then add the download link to the website.
- [ ] Publish the updated setup page through the manual GitHub Pages workflow.

The installer targets Windows 10 1903 or later, x64. Deferred for now: clean-PC
and reboot checks, expanded DuckStation discovery/import cases, alternate music
setup, and the rest of the packaged failure matrix. These are not preview
release blockers. Do not describe the current coverage as clean-machine testing.

Keep game-derived code/assets, retail BIOS, music packs and player saves outside
public release inputs. Package only the explicit source allowlist. The prepared
runtime has battle/movie native units and interpreter fallback elsewhere; do not
promise the development build's complete native-overlay coverage.

Only add a download button once the asset is publicly available and verified.
Retain the source-build guide as an alternative after publishing.
