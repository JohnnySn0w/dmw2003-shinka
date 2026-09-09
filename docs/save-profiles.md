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

## Import a card

From the repository root, choose a new destination directory:

```powershell
$sourceCard = 'PATH\TO\DuckStation\memcards\Digimon World 2003 (Europe) (En,Fr,De,Es,It)_1.mcd'
$testProfile = Join-Path (Get-Location) 'output/progressed-test-saves'
if (Test-Path -LiteralPath $testProfile) { throw 'Choose a new test profile.' }
$cardBytes = [IO.File]::ReadAllBytes($sourceCard)
if ($cardBytes.Length -ne 131072 -or $cardBytes[0] -ne 0x4D -or $cardBytes[1] -ne 0x43) {
    throw 'Expected a raw 128 KiB PlayStation memory card with an MC header.'
}
New-Item -ItemType Directory -Path $testProfile -ErrorAction Stop | Out-Null
$copiedCard = Join-Path $testProfile 'card1.mcd'
[IO.File]::WriteAllBytes($copiedCard, $cardBytes)
if ((Get-FileHash -LiteralPath $sourceCard).Hash -ne (Get-FileHash -LiteralPath $copiedCard).Hash) {
    throw 'Card changed during import; do not use this copy.'
}
```

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
