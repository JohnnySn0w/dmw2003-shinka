# Save profiles and DuckStation imports

The Windows runtime accepts raw 128 KiB PlayStation memory cards. Copy a
DuckStation `.mcd` into a new local profile as `card1.mcd`, then load it with the
game's **Continue** command. DuckStation `.sav` files are emulator savestates;
they are not interchangeable with this runtime's `.pst` savestates.

Keep the source card and ordinary player profile separate from test profiles.
Do not replace a card while a runtime using it is open. Each profile also holds
its own native savestates, so diagnostic slots can be reused across profiles.
Mod settings currently apply across profiles through the runtime's
`build-windows/Release/mods/state.toml`.

## Find a card or profile

From the repository root:

```powershell
python tools/save_profiles.py list
```

This prints absolute profile paths and the `card1.mcd` / `card2.mcd` files it
finds under `output/`, up to three directory levels down. It includes diagnostic
profiles; it does not guess which profile a running game is using. The launch
script's default remains `output/player-saves`. Use a narrower root or a greater
depth for a custom layout:

```powershell
python tools/save_profiles.py list --root 'output/title-screen' --depth 2
python tools/save_profiles.py inspect 'output/player-saves/card1.mcd'
```

`inspect` checks the raw card's size and MC header and displays its SHA-256
fingerprint. It does not repair cards or validate every saved game's contents.
All commands accept `--json` for tooling.

## Import a card

Close the emulator writing the source card and choose a new destination profile:

```powershell
python tools/save_profiles.py import-card 'PATH\TO\DuckStation\memcards\game_1.mcd' 'output/progressed-test-saves'
```

The helper checks the card format, creates `card1.mcd` with exclusive creation,
flushes and verifies the copy, and confirms that the source still matches. It
never overwrites an existing profile, even an empty one. If verification or
writing fails, it removes only its newly created files. A local, Git-ignored
`shinka-card-import.json` records the source path, timestamp and fingerprint.
Use `--slot 2` to import as `card2.mcd` instead; the destination must still be new.

Launch with the new profile:

```powershell
./tools/launch_windows.ps1 -DiscCue 'PATH\TO\game.cue' -RetailBios 'PATH\TO\bios.bin' -SaveDirectory 'output/progressed-test-saves'
```

`-SaveDirectory` accepts an absolute path or a path relative to the calling
directory. Omit it to use the existing `output/player-saves` default. Use the
same BIOS backend as your normal launch. The runtime creates a blank second
card if none is present.

All cards, native states, screenshots and import provenance stay under ignored
`output/`; none should be committed to the repository.

## Verification

Synthetic tests cover exact copying, source preservation, existing-profile
refusal, invalid headers and sizes, slot selection, a changing source, disk-write
failure cleanup, unrelated-file preservation and bounded profile discovery.
These are import-tool checks, separate from the game's [save/load timing and
compatibility tests](save-timing.md).

A September 11 command-line check imported a diagnostic copy of the player's
card into a fresh profile. Independent source/destination SHA-256 checks matched,
and both the card and provenance file were confirmed excluded from Git. Profile
discovery also found the installed build's two cards under `output/title-screen/saves`.
