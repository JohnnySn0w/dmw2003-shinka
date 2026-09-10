"""Fetch the pinned CC0 audition banks into local storage (Python + 7-Zip)."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

CATALOG = Path(__file__).resolve().parents[1] / 'assets/music/cc0-banks.json'


def checked(data, digest):
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('Asset SHA-256 mismatch; refusing changed content')
    return data


def fetch(output, seven_zip):
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    output.mkdir(parents=True, exist_ok=True)
    for name, bank in catalog['banks'].items():
        dest = output / f'{name}.sf2'
        if dest.exists():
            checked(dest.read_bytes(), bank['sha256'])
            print(f'{name}: verified existing bank')
            continue
        archive = output / bank['url'].rsplit('/', 1)[1]
        if archive.exists():
            checked(archive.read_bytes(), bank['archive_sha256'])
        else:
            with urllib.request.urlopen(bank['url'], timeout=60) as response:
                data = response.read(64 * 1024 * 1024 + 1)
            checked(data, bank['archive_sha256'])
            with archive.open('xb') as file:
                file.write(data)
        # Read only the pinned member to memory. Never extract archive paths.
        if archive.name.endswith('.tar.xz'):
            with tarfile.open(archive) as package:
                member = package.getmember(bank['member'])
                if not member.isfile() or member.size > 64 * 1024 * 1024:
                    raise ValueError('Unexpected SoundFont archive member')
                with package.extractfile(member) as file:
                    data = file.read()
        else:
            data = subprocess.run([seven_zip, 'e', '-so', str(archive), bank['member']],
                                  check=True, capture_output=True).stdout
        checked(data, bank['sha256'])
        with dest.open('xb') as file:
            file.write(data)
        print(f'{name}: installed verified CC0 bank')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('output/music-banks'))
    parser.add_argument('--seven-zip', default=shutil.which('7z') or '7z')
    args = parser.parse_args()
    try:
        fetch(args.output, args.seven_zip)
    except (OSError, ValueError, subprocess.CalledProcessError, tarfile.TarError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
