param(
    [Parameter(Mandatory=$true)][string]$DiscCue,
    [string]$RetailBios = '',
    [string]$ControllerMappings = '',
    [ValidateSet(1,2,3,4)][int]$ExpMultiplier,
    [string]$Python = 'python',
    [switch]$Headless,
    [switch]$HoldOnGuestExit,
    [int]$DebugPort = 4380
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$disc = (Resolve-Path -LiteralPath $DiscCue).Path
$runtime = Join-Path $projectRoot 'build-windows/Release/dmw2003-shinka.exe'
if (-not (Test-Path -LiteralPath $runtime)) { throw 'Run tools/build_windows.ps1 first.' }
if ($PSBoundParameters.ContainsKey('ExpMultiplier')) {
    if (Get-Process -Name 'dmw2003-shinka' -ErrorAction SilentlyContinue) {
        throw 'Close the game before changing the EXP setting.'
    }
    $cueText = Get-Content -LiteralPath $disc -Raw
    $files = [regex]::Matches($cueText, '(?im)^\s*FILE\s+"([^"]+)"\s+BINARY\s*$')
    if ($files.Count -ne 1) { throw 'EXP configuration requires the supported single-BIN CUE.' }
    $discBin = Join-Path (Split-Path $disc -Parent) $files[0].Groups[1].Value
    & $Python (Join-Path $PSScriptRoot 'configure_exp.py') --disc-bin $discBin --multiplier $ExpMultiplier
    if ($LASTEXITCODE -ne 0) { throw 'EXP configuration failed; game was not launched.' }
}
$arguments = @('--game', (Join-Path $projectRoot 'game.toml'), '--disc', $disc,
    '--memcard-dir', (Join-Path $projectRoot 'output/player-saves'), '--debug-port', "$DebugPort", '--no-launcher')
if ($RetailBios) { $arguments += @('--bios', (Resolve-Path -LiteralPath $RetailBios).Path) }
if ($Headless) { $arguments += '--headless' }
$mappingFile = if ($ControllerMappings) { (Resolve-Path -LiteralPath $ControllerMappings).Path } else { '' }
$previousMappingFile = [Environment]::GetEnvironmentVariable('SDL_GAMECONTROLLERCONFIG_FILE', 'Process')
$previousExitHalt = [Environment]::GetEnvironmentVariable('PSX_EXIT_HALT', 'Process')
Push-Location $projectRoot
try {
    if ($mappingFile) { $env:SDL_GAMECONTROLLERCONFIG_FILE = $mappingFile }
    if ($HoldOnGuestExit) { $env:PSX_EXIT_HALT = '1' }
    & $runtime @arguments
} finally {
    if ($mappingFile) {
        [Environment]::SetEnvironmentVariable('SDL_GAMECONTROLLERCONFIG_FILE', $previousMappingFile, 'Process')
    }
    if ($HoldOnGuestExit) {
        [Environment]::SetEnvironmentVariable('PSX_EXIT_HALT', $previousExitHalt, 'Process')
    }
    Pop-Location
}
