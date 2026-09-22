"""Create MP3 listening copies and verified lossless FLAC stems locally."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import wave
import zipfile

from arrange_labelled_music import write_index


def run(arguments):
    return subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', *arguments],
                          check=True, capture_output=True).stdout


def package(root):
    root = root.resolve()
    report = json.loads((root/'arrangements.json').read_text())
    for track in report['tracks']:
        folder = (root/track['id']).resolve()
        if folder.parent != root:
            raise ValueError('Track path escapes output')
        for palette in ('sampled', 'ds', 'chip'):
            dest = folder/(palette+'.mp3')
            if not dest.exists():
                run(['-i', str(folder/(palette+'.wav')), '-codec:a', 'libmp3lame',
                     '-q:a', '2', '-threads', '1', '-metadata',
                     'title='+track['title']+' — '+palette.title(), str(dest)])
            for part in track['parts']:
                source = folder/f'{palette}-part-{part["part"]:02}.wav'
                dest = source.with_suffix('.flac')
                if not source.exists():
                    if not dest.exists():
                        raise ValueError(f'Missing stem: {source}')
                    continue
                if not dest.exists():
                    run(['-i', str(source), '-codec:a', 'flac', '-compression_level', '5',
                         '-threads', '1', str(dest)])
                with wave.open(str(source)) as f:
                    if (f.getnchannels(), f.getsampwidth(), f.getframerate()) != (2, 2, 44100):
                        raise ValueError('Unexpected stem format')
                    original = f.readframes(f.getnframes())
                decoded = run(['-i', str(dest), '-f', 's16le', '-acodec', 'pcm_s16le', '-'])
                if hashlib.sha256(original).digest() != hashlib.sha256(decoded).digest():
                    raise ValueError(f'FLAC changed PCM: {dest}')
                # Only this generated WAV, after byte-identical lossless decode.
                source.unlink()
        print('Packaged', track['id'], flush=True)
    write_index(root, report)
    archive = root/'Shinka-labeled-listening-samples.zip'
    if archive.exists():
        raise ValueError('Listening archive already exists')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for track in report['tracks']:
            for palette in ('sampled', 'ds', 'chip'):
                path = root/track['id']/(palette+'.mp3')
                z.write(path, f'{track["id"]}/{path.name}')
        z.writestr('README.txt', f'Shinka instrument auditions: {len(report["tracks"])} completed notebook tracks, three palettes.\n'
                   'First-pass offline arrangements of the original game sequences, not new compositions.\n'
                   'The listening folder also contains full WAV mixes, lossless FLAC stems and instrument notes.\n'
                   'Some labeled instruments use explicitly documented substitutes. No live game mappings changed.\n')
    write_index(root, report)
    print(archive, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    package(parser.parse_args().directory)
