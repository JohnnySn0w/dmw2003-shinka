"""Stage an explicit source-only SDK; never package a development runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

FRAMEWORK_REVISION = 'f3786825411983a06257865db7bd7538fc68267a'
CANDIDATE_REVISION = '6ae36f9564b0c81b64428aa5355375d945d56d53'
SHINKA_TREES = ('src/', 'tools/', 'mods/')
SHINKA_FILES = ('CMakeLists.txt', 'game.toml', 'README.md',
                'assets/shinka.png', 'assets/shinka.ico', 'assets/branding/shinka-title.png')
FRAMEWORK_TREES = ('runtime/', 'recompiler/', 'bios/', 'tools/', 'include/',
                   'src/', 'lib/', 'host/', 'third_party/', 'cmake/', 'assets/')
FRAMEWORK_FILES = ('CMakeLists.txt', 'LICENSE', 'README.md', 'psxrecomp_cli.py')


def git(root, *args):
    return subprocess.check_output(['git', '-c', f'safe.directory={Path(root).resolve().as_posix()}',
                                    '-C', str(root), *args])


def selected(name, trees, files):
    return name in files or name.startswith(trees)


def build_sdk(repo, candidate, destination):
    repo, candidate, destination = map(Path, (repo, candidate, destination))
    framework = candidate / 'psxrecomp'
    for root, expected in ((candidate, CANDIDATE_REVISION), (framework, FRAMEWORK_REVISION)):
        if git(root, 'rev-parse', 'HEAD').decode().strip() != expected:
            raise ValueError(f'Unexpected source revision: {root}')
        if git(root, 'diff', '--name-only').strip():
            raise ValueError(f'Pinned dependency has local modifications: {root}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    records = []
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for root, prefix, trees, files in (
                (repo, 'shinka/', SHINKA_TREES, SHINKA_FILES),
                (framework, 'framework/', FRAMEWORK_TREES, FRAMEWORK_FILES)):
            names = git(root, 'ls-files', '-z').decode().split('\0')
            for name in sorted(filter(None, names)):
                if not selected(name, trees, files):
                    continue
                path = root / name
                if path.is_symlink() or not path.is_file():
                    # Optional network/rewind gitlinks are deliberately not bundled.
                    continue
                if root == framework and '/tests/' in name and path.suffix.lower() in ('.mcd', '.bin', '.exe', '.dll'):
                    continue  # upstream binary test fixtures are not release inputs
                if path.suffix.lower() in ('.mcd', '.pst', '.sav', '.exe', '.dll', '.cue', '.iso', '.img', '.chd'):
                    raise ValueError('Unexpected binary in source payload: ' + name)
                if path.suffix.lower() == '.bin' and not (root == framework and name == 'bios/openbios.bin'):
                    raise ValueError('Unexpected disc/BIOS data in source payload: ' + name)
                payload = path.read_bytes()
                archive.writestr(prefix + name, payload)
                records.append(dict(path=prefix + name, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload)))
        seeds = git(candidate, 'show', f'{CANDIDATE_REVISION}:seeds/ghidra_funcs.txt')
        archive.writestr('seeds/ghidra_funcs.txt', seeds)
        records.append(dict(path='seeds/ghidra_funcs.txt', sha256=hashlib.sha256(seeds).hexdigest(), bytes=len(seeds)))
        revision = git(repo, 'rev-parse', 'HEAD').decode().strip()
        archive.writestr('sdk-manifest.json', json.dumps(dict(schema=1, revision=revision,
            framework=FRAMEWORK_REVISION, candidate=CANDIDATE_REVISION, files=records), indent=2))
    record = dict(schema=1, revision=revision, sdk_sha256=hashlib.file_digest(destination.open('rb'), 'sha256').hexdigest(),
                  sdk_bytes=destination.stat().st_size, expanded_bytes=sum(r['bytes'] for r in records))
    destination.with_suffix('.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_sdk(args.repo, args.candidate, args.output), indent=2))
