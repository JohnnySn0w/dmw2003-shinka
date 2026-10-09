"""Cancellable local preparation using a pinned portable toolchain and source SDK."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import urllib.request
import uuid

from setup_core import (TOOLCHAIN, Cancelled, atomic_json, check_cancel, hash_file,
                        safe_extract, validate_disc)
from configure_journal import select_journal


def ensure_toolchain(root, cancel, notify):
    root = Path(root)
    installed = root / 'toolchains' / TOOLCHAIN['version']
    marker = installed / 'shinka-verified.json'
    if marker.is_file() and json.loads(marker.read_text()).get('sha256') == TOOLCHAIN['sha256']:
        if all((installed / p).is_file() for p in ('bin/cmake.exe', 'bin/clang.exe', 'bin/ninja.exe', 'python/python.exe')):
            return installed
    cache = root / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / f"toolchain-{TOOLCHAIN['version']}.zip"
    if not archive.exists() or hash_file(archive, cancel=cancel) != TOOLCHAIN['sha256']:
        partial = cache / (archive.name + '.part')
        notify('Downloading preparation tools', 0, TOOLCHAIN['bytes'])
        try:
            request = urllib.request.Request(TOOLCHAIN['url'], headers={'User-Agent': 'Shinka-Setup'})
            with urllib.request.urlopen(request, timeout=30) as source, partial.open('wb') as output:
                total = 0
                while block := source.read(1024 * 1024):
                    check_cancel(cancel)
                    total += len(block)
                    if total > TOOLCHAIN['bytes']:
                        raise ValueError('Tool download exceeded its pinned size.')
                    output.write(block)
                    notify('Downloading preparation tools', total, TOOLCHAIN['bytes'])
            if total != TOOLCHAIN['bytes'] or hash_file(partial, cancel=cancel) != TOOLCHAIN['sha256']:
                raise ValueError('Preparation-tool download failed its integrity check. Retry to download it again.')
            partial.replace(archive)
        finally:
            partial.unlink(missing_ok=True)
    notify('Unpacking preparation tools', None, None)
    staging = root / 'toolchains' / ('.staging-' + uuid.uuid4().hex)
    staging.mkdir(parents=True)
    safe_extract(archive, staging, cancel)
    atomic_json(staging / 'shinka-verified.json', dict(sha256=TOOLCHAIN['sha256']))
    if installed.exists():
        # Retain a damaged prior installation for diagnosis; never merge versions.
        installed.rename(installed.with_name('replaced-' + uuid.uuid4().hex))
    staging.rename(installed)
    return installed


def portable_environment(toolchain):
    env = os.environ.copy()
    windows = Path(env.get('SystemRoot', 'C:/Windows'))
    # No host compiler, Python or developer shell is used by preparation.
    env['PATH'] = os.pathsep.join(map(str, (toolchain/'bin', toolchain/'python', windows/'System32', windows)))
    for key in ('PYTHONHOME', 'PYTHONPATH', 'CC', 'CXX', 'INCLUDE', 'LIB', 'LIBPATH', 'CMAKE_PREFIX_PATH', 'ZLIB_ROOT', 'SDL3_DIR'):
        env.pop(key, None)
    env['PYTHONNOUSERSITE'] = '1'
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    env['RETCOMM_TOOLCHAIN_DIR'] = str(toolchain)
    env['CCACHE_DISABLE'] = '1'
    return env


def extract_source(sdk, work, cancel):
    """Only a completely unpacked SDK becomes resumable source input."""
    source = work/'source'
    if (source/'.sdk-ready.json').is_file():
        return
    staging = work/('source-staging-' + uuid.uuid4().hex[:8])
    safe_extract(sdk, staging, cancel)
    check_cancel(cancel)
    atomic_json(staging/'.sdk-ready.json', dict(complete=True))
    if source.exists():
        source.rename(work/('source-interrupted-' + uuid.uuid4().hex[:8]))
    staging.rename(source)


def run(command, cwd, env, cancel, log, notify, stage, new_console=False):
    check_cancel(cancel)
    notify(stage, None, None)
    log.write('\n' + subprocess.list2cmdline(list(map(str, command))) + '\n')
    log.flush()
    options = {}
    if os.name == 'nt':
        options['creationflags'] = subprocess.CREATE_NO_WINDOW
        if new_console:
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = subprocess.SW_HIDE
            options.update(creationflags=subprocess.CREATE_NEW_CONSOLE, startupinfo=startup)
    proc = subprocess.Popen(list(map(str, command)), cwd=cwd, env=env, stdout=log,
                            stderr=subprocess.STDOUT, **options)
    while proc.poll() is None:
        if cancel.wait(.15):
            if os.name == 'nt':
                subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/taskkill.exe'), '/PID', str(proc.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                proc.terminate()
            proc.wait()
            raise Cancelled('Preparation cancelled. The last working installation and saves are unchanged.')
    if proc.returncode:
        raise RuntimeError(f'{stage} failed. Your existing installation and saves are unchanged. See the preparation log for details, then retry.')


def configure_codegen_paths(framework):
    """Use Unicode source lists and avoid Ninja's ANSI .bat hash wrappers.

    Only the extracted setup copy is patched. The canonical source list and
    hashing algorithm stay unchanged, so overlay compatibility is preserved.
    """
    framework = Path(framework)
    edits = (
        ('runtime/check_generated_sources.cmake',
         'file(STRINGS "${SOURCES_FILE}" _sources)',
         'file(STRINGS "${SOURCES_FILE}" _sources ENCODING UTF-8)'),
        ('recompiler/CMakeLists.txt', '"-DSRCS=${PSXRECOMP_CODEGEN_HASH_SRCS}"',
         '"-DSHINKA_CODEGEN_ROOT=${CMAKE_CURRENT_SOURCE_DIR}/.."'),
        ('runtime/runtime.cmake', '"-DSRCS=${_codegen_srcs}"',
         '"-DSHINKA_CODEGEN_ROOT=${PSXRECOMP_ROOT}"'),
        ('runtime/hash_codegen.cmake', 'set(_cat "")',
         'if(DEFINED SHINKA_CODEGEN_ROOT)\n'
         '    set(PSXRECOMP_CODEGEN_HASH_ROOT "${SHINKA_CODEGEN_ROOT}")\n'
         '    include("${SHINKA_CODEGEN_ROOT}/runtime/codegen_hash_sources.cmake")\n'
         '    set(SRCS ${PSXRECOMP_CODEGEN_HASH_SRCS})\n'
         'endif()\n\nset(_cat "")'),
    )
    pending = []
    for name, old, new in edits:
        path = framework/name
        text = path.read_text(encoding='utf-8')
        if text.count(new) == 1:
            continue
        if text.count(old) != 1:
            raise ValueError('The setup codegen path hook changed: ' + name)
        pending.append((path, text.replace(old, new)))
    for path, text in pending:
        path.write_text(text, encoding='utf-8')


def prepare(cue, sdk, root, cancel=None, notify=lambda *args: None, toolchain=None):
    cancel = cancel or threading.Event()
    root, sdk = Path(root).resolve(), Path(sdk).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(root).free < 6 * 1024**3:
        raise OSError('Preparation needs at least 6 GB of free space for tools and temporary build files.')
    disc = validate_disc(cue, cancel, lambda done, total: notify('Checking your disc', done, total))
    metadata = json.loads(sdk.with_suffix('.json').read_text(encoding='utf-8'))
    if hash_file(sdk, cancel=cancel) != metadata['sdk_sha256']:
        raise ValueError('The setup source package failed its integrity check. Reinstall Shinka.')
    toolchain = Path(toolchain).resolve() if toolchain else ensure_toolchain(root, cancel, notify)
    env = portable_environment(toolchain)
    build_id = metadata['revision'][:12] + '-' + uuid.uuid4().hex[:8]
    work = root / 'builds' / build_id
    for marker in sorted((root/'builds').glob('*/preparation.json'), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            previous = json.loads(marker.read_text(encoding='utf-8'))
            if previous.get('sdk', {}).get('sdk_sha256') == metadata['sdk_sha256']:
                if previous.get('state') == 'ready' and (Path(previous['runtime'])/'dmw2003-shinka.exe').is_file():
                    return dict(previous, disc=disc)
                if (marker.parent/'source/.sdk-ready.json').is_file():
                    work = marker.parent
                    break
        except (OSError, ValueError, KeyError):
            continue
    work.mkdir(parents=True, exist_ok=True)
    atomic_json(work / 'preparation.json', dict(schema=1, state='building', disc=disc, sdk=metadata))
    notify('Preparing local game files', None, None)
    extract_source(sdk, work, cancel)
    source, framework = work/'source/shinka', work/'source/framework'
    configure_codegen_paths(framework)
    cmake, python = toolchain/'bin/cmake.exe', toolchain/'python/python.exe'
    compiler_args = ['-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Release',
                     f'-DCMAKE_C_COMPILER={toolchain / "bin/clang.exe"}',
                     f'-DCMAKE_CXX_COMPILER={toolchain / "bin/clang++.exe"}',
                     f'-DCMAKE_MAKE_PROGRAM={toolchain / "bin/ninja.exe"}']
    log_path = work/'prepare.log'
    with log_path.open('w', encoding='utf-8') as log:
        def execute(command, stage, cwd=source):
            build = command[0] == cmake and '--build' in command
            if build:
                command = [python, source/'tools/setup_build_console.py', *command]
            run(command, cwd, env, cancel, log, notify, stage, new_console=build)
        emitter_build = work/'emitters'
        execute([cmake, '-S', framework/'recompiler', '-B', emitter_build, *compiler_args,
                 f'-DCMAKE_PROJECT_PSXRecomp_INCLUDE={source / "tools/setup_emitter_paths.cmake"}',
                 '-DPSXRECOMP_ENABLE_CHD=OFF', '-DBUILD_TESTING=OFF', '-DPSXRECOMP_STATIC_CLI=ON'], 'Preparing conversion tools')
        execute([cmake, '--build', emitter_build, '--target', 'psxrecomp-game', 'psxrecomp-bios', '--parallel', '2'], 'Building conversion tools')
        # Stamp the same source hash as the emitter before compiling overlays.
        # The regular runtime build does this too, but happens later in setup.
        stamp = work/'stamp-codegen.cmake'
        stamp.write_text('\n'.join((
            f'set(PSXRECOMP_CODEGEN_HASH_ROOT "{framework.as_posix()}")',
            'include("${PSXRECOMP_CODEGEN_HASH_ROOT}/runtime/codegen_hash_sources.cmake")',
            'set(SRCS ${PSXRECOMP_CODEGEN_HASH_SRCS})',
            'set(OUT "${PSXRECOMP_CODEGEN_HASH_ROOT}/runtime/include/overlay_codegen_hash.h")',
            'include("${PSXRECOMP_CODEGEN_HASH_ROOT}/runtime/hash_codegen.cmake")',
        )), encoding='utf-8')
        execute([cmake, '-P', stamp], 'Checking conversion compatibility')
        # Absolute inputs avoid the emitter's ancestor/.git discovery, including
        # when a setup test happens to live inside an unrelated repository.
        bios_profile = framework/'OpenBIOS.setup.toml'
        bios_text = (framework/'bios/OpenBIOS.toml').read_text(encoding='utf-8')
        for relative in ('bios/openbios.bin', 'recompiler/seeds/openbios_elf_seeds.json', 'generated'):
            quoted = '"' + relative + '"'
            if bios_text.count(quoted) != 1:
                raise ValueError('The OpenBIOS preparation profile changed; review its paths.')
            bios_text = bios_text.replace(quoted, json.dumps((framework/relative).as_posix()))
        bios_profile.write_text(bios_text, encoding='utf-8')
        execute([emitter_build/'psxrecomp-bios.exe', '--config', bios_profile], 'Preparing the included OpenBIOS', framework)
        extract = [python, source/'tools/audit_disc.py', disc['binary'], '--output', source/'extracted/audit', '--extract-exe']
        for name in ('STFGTREP.PRO', 'STGDGLAB.PRO', 'FIELDSTG.PRO', 'STSTATUS.PRO', 'FIGHTSTG.PRO', 'STDWTITL.PRO'):
            extract += ['--extract-file', name]
        execute(extract, 'Reading game files from your disc')
        (source/'output').mkdir(exist_ok=True)
        seeds = source/'output/ghidra_funcs.txt'
        shutil.copy2(work/'source/seeds/ghidra_funcs.txt', seeds)
        execute([emitter_build/'psxrecomp-game.exe', source/'extracted/audit/SLES_039.36', '--project-root', framework,
                 '--seeds', seeds, '--out-dir', source/'output/recompiled', '--strict'], 'Preparing game code')
        for unit, module in (('battle', 'FIGHTSTG.PRO'), ('movie', 'STDWTITL.PRO')):
            if (source/f'output/{unit}-native/provenance.json').is_file():
                continue
            # Each attempt owns a distinct output folder; interrupted converter
            # output is retained rather than mistaken for a completed unit.
            native_output = source/f'output/{unit}-native'
            if native_output.exists():
                native_output.rename(native_output.with_name(unit + '-interrupted-' + uuid.uuid4().hex[:8]))
            execute([python, source/f'tools/build_{unit}_native.py', '--module', source/'extracted/audit'/module,
                     '--framework', framework, '--recompiler', emitter_build/'psxrecomp-game.exe',
                     '--output', source/f'output/{unit}-native'], f'Preparing {unit} optimizations')
        runtime_build = work/'runtime-build'
        execute([cmake, '-S', source, '-B', runtime_build, *compiler_args,
                 f'-DPSXRECOMP_ROOT={framework}', f'-DPython3_EXECUTABLE={python}',
                 f'-DZLIB_ROOT={toolchain / "deps"}', f'-DSDL3_DIR={toolchain / "deps/lib/cmake/SDL3"}',
                 '-DPSX_RECOMP_UI=OFF', '-DPSX_REWIND=OFF', '-DPSX_NETPLAY=OFF', '-DPSX_PGXP_VARIANT=OFF',
                 '-DPSX_STATIC_RUNTIME=ON', '-DPSX_DEBUG_TOOLS=ON', '-DSHINKA_BUILD_TESTS=OFF',
                 '-DPSXRECOMP_BIOS_STEMS=OpenBIOS', '-DSHINKA_MUSIC_PACK=',
                 f'-DSHINKA_BATTLE_OVERLAY_SOURCE={source / "output/battle-native/overlays_static.c"}',
                 f'-DSHINKA_MOVIE_OVERLAY_SOURCE={source / "output/movie-native/overlays_static.c"}'], 'Configuring Shinka')
        execute([cmake, '--build', runtime_build, '--target', 'shinka', '--parallel', '2'], 'Building Shinka — this can take several minutes')
    check_cancel(cancel)
    runtime = work/'runtime'
    runtime.mkdir(exist_ok=True)
    for name in ('dmw2003-shinka.exe', 'game.toml', 'psx_game_version.txt'):
        if (runtime_build/name).is_file():
            shutil.copy2(runtime_build/name, runtime/name)
    for name in ('assets', 'bios', 'mods'):
        shutil.copytree(runtime_build/name, runtime/name, dirs_exist_ok=True)
    # Runtime assets use paths relative to game.toml during initial startup.
    (runtime/'extracted/audit').mkdir(parents=True, exist_ok=True)
    shutil.copy2(source/'extracted/audit/SLES_039.36', runtime/'extracted/audit/SLES_039.36')
    state = runtime/'mods/state.toml'
    state.write_text(select_journal(state.read_text(encoding='utf-8') if state.exists() else '', True), encoding='utf-8')
    record = dict(schema=1, state='ready', runtime=str(runtime), disc=disc,
                  revision=metadata['revision'], sdk=metadata, log=str(log_path))
    atomic_json(work/'preparation.json', record)
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cue', required=True)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--toolchain', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.cue, args.sdk, args.data, toolchain=args.toolchain,
                            notify=lambda stage, done, total: print(stage, done or '', total or '', flush=True)), indent=2))
