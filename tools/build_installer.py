"""Freeze the source-only launcher and build a per-user Windows installer.

Run using a packaging venv with PyInstaller==6.16.0; pass a verified Inno Setup
ISCC.exe and source SDK built by package_setup_sdk.py. No game runtime is copied.
"""
import argparse
import json
import importlib.metadata
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from setup_core import hash_file


def build(sdk, output, iscc, version):
    repo = Path(__file__).resolve().parents[1]
    sdk, output, iscc = map(lambda p: Path(p).resolve(), (sdk, output, iscc))
    record = json.loads(sdk.with_suffix('.json').read_text(encoding='utf-8'))
    if hash_file(sdk) != record['sdk_sha256']:
        raise ValueError('Source SDK integrity check failed.')
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                    '--onedir', '--windowed', '--name', 'Shinka',
                    '--icon', str(repo/'assets/shinka.ico'),
                    '--add-data', str(repo/'assets/shinka.ico') + ';assets',
                    '--distpath', str(output/'dist'), '--workpath', str(output/'work'),
                    '--specpath', str(output), str(repo/'tools/shinka_launcher.py')], check=True, cwd=repo)
    stage = output/'dist/Shinka'
    shutil.copy2(sdk, stage/'sdk.zip')
    shutil.copy2(sdk.with_suffix('.json'), stage/'sdk.json')
    notices = stage/'notices'
    notices.mkdir(exist_ok=True)
    shutil.copy2(Path(sys.base_prefix)/'LICENSE.txt', notices/'Python-LICENSE.txt')
    pyinstaller = importlib.metadata.distribution('pyinstaller')
    for item in pyinstaller.files:
        if item.name == 'COPYING.txt':
            shutil.copy2(pyinstaller.locate_file(item), notices/'PyInstaller-COPYING.txt')
    for license_path in (Path(sys.base_prefix)/'tcl').glob('*/license.terms'):
        shutil.copy2(license_path, notices/(license_path.parent.name + '-license.terms'))
    # Preserve upstream source licenses alongside the installer's visible files.
    with zipfile.ZipFile(sdk) as archive:
        for name in archive.namelist():
            if Path(name).name.lower().startswith(('license', 'copying', 'copyright')):
                dest = notices/name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(archive.read(name))
    (notices/'README.txt').write_text(
        'Shinka uses PSXRecomp (PolyForm Noncommercial 1.0.0), OpenBIOS (MIT), '
        'Python, Tcl/Tk, PyInstaller and their bundled dependencies. '
        'Source dependencies and their license notices are included in sdk.zip. '
        'Python/Tcl/Tk license files are included in _internal. '
        'Preparation tools are downloaded separately from the pinned '
        'RetroPorting-Toolchains release with their own notices. '
        'No retail disc, retail BIOS, generated game code, or personal save is included.\n', encoding='utf-8')
    subprocess.run([str(iscc), '/DStage=' + str(stage), '/DRelease=' + str(output/'release'),
                    '/DVersion=' + version, str(repo/'packaging/shinka.iss')], check=True, cwd=repo)
    installer = output/'release'/f'Shinka-Setup-{version}-windows-x64.exe'
    installer.with_suffix('.sha256').write_text(hash_file(installer) + '  ' + installer.name + '\n', encoding='utf-8')
    return installer


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--iscc', required=True, type=Path)
    parser.add_argument('--version', default='0.1.0')
    args = parser.parse_args()
    print(build(args.sdk, args.output, args.iscc, args.version))
