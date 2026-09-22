"""Fetch pinned CC0 samples used by arrange_labelled_music; no game files."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import quote
from urllib.request import urlopen

from music_fetch_banks import checked

CATALOG = Path(__file__).resolve().parents[1]/'assets/music/labelled-audition-samples.json'


def local(root, name):
    path = (root/name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Instrument path escapes output')
    return path


def download(path, url, digest):
    if path.exists():
        checked(path.read_bytes(), digest)
        return
    with urlopen(url, timeout=60) as r:
        data = checked(r.read(64*1024*1024+1), digest)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(data)


def fetch(root, seven_zip):
    spec = json.loads(CATALOG.read_text())
    root.mkdir(parents=True, exist_ok=True)
    for sample in spec['samples']:
        url = ('https://raw.githubusercontent.com/sgossner/'+sample['repo']+'/'+
               sample['revision']+'/'+quote(sample['path']))
        download(local(root, sample['file']), url, sample['sha256'])
    for archive in spec['archives']:
        path = local(root, archive['name']+'.7z')
        download(path, archive['url'], archive['sha256'])
        for member in archive['members']:
            target = local(root, archive['name']+'/'+member['member'])
            if target.exists():
                checked(target.read_bytes(), member['sha256'])
                continue
            # Extract only pinned members to stdout; archive paths never choose
            # a filesystem destination, and each result has its own digest.
            data = subprocess.run([seven_zip, 'e', '-so', str(path), member['member']],
                                  capture_output=True, check=True).stdout
            checked(data, member['sha256'])
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as f:
                f.write(data)
    (root/'catalog.json').write_text(json.dumps(spec['samples'], indent=2)+'\n')
    print(f'Verified {len(spec["samples"])} samples and {len(spec["archives"])} instrument archives.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('output/labelled-instruments'))
    parser.add_argument('--seven-zip', default=shutil.which('7z') or '7z')
    args = parser.parse_args()
    fetch(args.output, args.seven_zip)
