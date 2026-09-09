param(
    [Parameter(Mandatory=$true)][string]$DiscCue,
    [string]$RetailBios = '',
    [switch]$Headless,
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
Push-Location $projectRoot
try { & $runtime @arguments } finally { Pop-Location }
