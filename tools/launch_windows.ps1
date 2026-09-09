param(
    [Parameter(Mandatory=$true)][string]$DiscCue,
    [string]$RetailBios = '',
    [string]$ControllerMappings = '',
    [switch]$Headless,
    [switch]$HoldOnGuestExit,
    [int]$DebugPort = 4380
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$disc = (Resolve-Path -LiteralPath $DiscCue).Path
$runtime = Join-Path $projectRoot 'build-windows/Release/dmw2003-shinka.exe'
if (-not (Test-Path -LiteralPath $runtime)) { throw 'Run tools/build_windows.ps1 first.' }
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
