param(
    [Parameter(Mandatory=$true)][string]$DiscBin,
    [Parameter(Mandatory=$true)][string]$CandidateRoot,
    [string]$Python = 'python',
    [string]$RetailBios = '',
    [string]$OverlayCaptures = '',
    [int]$Jobs = 4
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$candidate = (Resolve-Path -LiteralPath $CandidateRoot).Path
$framework = Join-Path $candidate 'psxrecomp'
$disc = (Resolve-Path -LiteralPath $DiscBin).Path
$bios = if ($RetailBios) { (Resolve-Path -LiteralPath $RetailBios).Path } else { '' }
$captures = if ($OverlayCaptures) { (Resolve-Path -LiteralPath $OverlayCaptures).Path } else { '' }
$expectedFramework = 'f3786825411983a06257865db7bd7538fc68267a'
$expectedCandidate = '6ae36f9564b0c81b64428aa5355375d945d56d53'
$actualCandidate = & git -C $candidate rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $actualCandidate -ne $expectedCandidate) {
    throw "Expected game candidate revision $expectedCandidate (contains the audited seed file)"
}
$actualFramework = & git -C $framework rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $actualFramework -ne $expectedFramework) {
    throw "Expected PSXRecomp revision $expectedFramework"
}
if ((Get-FileHash -LiteralPath $disc -Algorithm SHA1).Hash.ToLowerInvariant() -ne '457cb233349ba841e03b33d8060f8fbcadd45cb3') {
    throw 'Unsupported disc hash; this baseline supports the audited European image only.'
}
function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed with exit code $LASTEXITCODE" }
}
Push-Location $projectRoot
try {
    Invoke-Checked $Python @('tools/audit_disc.py', $disc, '--output', 'extracted/audit', '--extract-exe', '--extract-file', 'STFGTREP.PRO', '--extract-file', 'STGDGLAB.PRO', '--extract-file', 'FIELDSTG.PRO', '--extract-file', 'STSTATUS.PRO')
    $emitterBuild = Join-Path $candidate 'build-recompiler'
    Invoke-Checked 'cmake' @('-S', "$framework/recompiler", '-B', $emitterBuild, '-G', 'Visual Studio 17 2022', '-A', 'x64', '-DPSXRECOMP_ENABLE_CHD=OFF', '-DBUILD_TESTING=OFF')
    Invoke-Checked 'cmake' @('--build', $emitterBuild, '--config', 'Release', '--target', 'psxrecomp-game', 'psxrecomp-bios', '--parallel', "$Jobs")
    Invoke-Checked "$emitterBuild/Release/psxrecomp-bios.exe" @('--config', "$framework/bios/OpenBIOS.toml")
    if ($bios) {
        if ((Get-FileHash -LiteralPath $bios -Algorithm MD5).Hash.ToLowerInvariant() -ne '924e392ed05558ffdb115408c263dccf') {
            throw 'The optional retail backend requires the audited SCPH-1001 BIOS image.'
        }
        Invoke-Checked "$emitterBuild/Release/psxrecomp-bios.exe" @('--config', "$framework/bios/SCPH1001.toml", '--rom', $bios)
    }
    Invoke-Checked "$emitterBuild/Release/psxrecomp-game.exe" @('extracted/audit/SLES_039.36', '--project-root', $candidate, '--seeds', "$candidate/seeds/ghidra_funcs.txt", '--out-dir', 'output/recompiled', '--strict')
    Copy-Item -LiteralPath "$candidate/seeds/ghidra_funcs.txt" -Destination 'output/ghidra_funcs.txt'
    $overlaySource = ''
    if ($captures) {
        Invoke-Checked $Python @("$framework/tools/compile_overlays.py", '--static', '--force', '--captures', $captures, '--game-toml', 'game.toml', '--recompiler', "$emitterBuild/Release/psxrecomp-game.exe", '--runtime-include', "$framework/runtime/include", '--out-dir', 'output/overlays', '--cps')
        $overlaySource = (Resolve-Path -LiteralPath 'output/overlays/overlays_static.c').Path
    }
    Invoke-Checked 'cmake' @('-S', '.', '-B', 'build-windows', '-G', 'Visual Studio 17 2022', '-A', 'x64', "-DPSXRECOMP_ROOT=$framework", "-DSHINKA_OVERLAY_SOURCE=$overlaySource", '-DPSX_RECOMP_UI=OFF', '-DPSX_REWIND=OFF', '-DPSX_DEBUG_TOOLS=ON', '-DPSX_PGXP_VARIANT=OFF', '-DCMAKE_BUILD_TYPE=Release')
    Invoke-Checked 'cmake' @('-S', '.', '-B', 'build-windows', '-DSHINKA_BUILD_TESTS=ON')
    Invoke-Checked 'cmake' @('--build', 'build-windows', '--config', 'Release', '--target', 'shinka', 'shinka_overlay_guard_test', 'shinka_journal_menu_test', 'shinka_menu_exp_test', 'shinka_evolution_chart_test', 'shinka_encounters_test', 'shinka_map_travel_test', 'shinka_dev_nav_test', '--parallel', "$Jobs")
    Invoke-Checked 'ctest' @('--test-dir', 'build-windows', '-C', 'Release', '--output-on-failure', '-R', '^(overlay_guard|journal_menu|menu_exp|evolution_chart|encounters|map_travel|dev_nav)$')
} finally {
    Pop-Location
}
