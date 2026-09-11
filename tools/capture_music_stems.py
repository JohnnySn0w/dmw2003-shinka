"""Capture aligned original-instrument stems from a copied-profile game session.

The running scene must play the requested bank. Dry stems retain native score,
ADSR, panning and delayed voices, but exclude the shared reverb/CD mix. The local
pack and owned export are required to identify sources; never publish these files.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import time
import wave

import numpy as np
from dev_nav import Navigator

RATE = 44100


def families(metadata, available):
    """Join programs with shared samples, including key-zone multisamples."""
    groups = []
    for program in metadata['bank']['programs']:
        samples = {t['sample'] for t in program['tones']} & available
        if not samples:
            continue
        programs = {program['program']}
        remaining = []
        for group in groups:
            if group['samples'] & samples:
                samples |= group['samples']
                programs |= group['programs']
            else:
                remaining.append(group)
        remaining.append(dict(samples=samples, programs=programs))
        groups = remaining
    return sorted(groups, key=lambda g: min(g['programs']))


def source_bank(pack, report, name):
    with pack.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    if digest != report['sha256'] or report.get('pack_format') != 'SHKMUS03':
        raise ValueError('Need a matching SHKMUS03 pack and routing report')
    index = next((i for i, bank in enumerate(report['banks']) if bank['bank'] == name), None)
    if index is None:
        raise ValueError('Bank is absent from the live pack')
    with pack.open('rb') as f:
        if f.read(8) != b'SHKMUS03' or struct.unpack('<II', f.read(8)) != (RATE, len(report['banks'])):
            raise ValueError('Invalid live pack header')
        for i, bank in enumerate(report['banks']):
            size, count = struct.unpack('<II', f.read(8))
            if count != len(bank['samples']) or not 16 <= size <= 524288:
                raise ValueError('Invalid live bank bounds')
            original = f.read(size)
            if i == index:
                return index, bank, original
            for _ in range(count):
                f.seek(12, 1)
                for _ in range(3):
                    frames, _loop = struct.unpack('<II', f.read(8))
                    if not 1 <= frames <= 132300:
                        raise ValueError('Invalid live wave bounds')
                    f.seek(frames * 2, 1)
    raise ValueError('Bank not found')


def write_wav(path, pcm, gain):
    output = np.rint(np.clip(pcm * gain, -32768, 32767)).astype('<i2')
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(output.tobytes())


def audition_window(pcm, seconds=8):
    length = min(len(pcm), round(seconds * RATE))
    step = RATE // 10
    energy = np.sum(pcm.astype(np.float64) ** 2, axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(energy)))
    starts = np.arange(0, len(pcm) - length + 1, step)
    start = int(starts[np.argmax(cumulative[starts + length] - cumulative[starts])])
    return start, pcm[start:start + length]


def assemble(output, metadata, bank, frames):
    offsets = {sample['id']: sample['body_offset'] for sample in metadata['bank']['samples']}
    available = {sample['sample'] for sample in bank['samples']}
    groups = families(metadata, available)
    parts = []
    for group in groups:
        pcm = np.zeros((frames, 2), dtype=np.int64)
        for sample in group['samples']:
            source = np.fromfile(output/'raw'/f'sample-{offsets[sample]}.s32le', dtype='<i4')
            if source.size != frames * 2:
                raise ValueError('Incomplete stem capture')
            pcm += source.reshape(-1, 2)
        peak = int(np.max(np.abs(pcm)))
        if peak:
            parts.append((group, pcm, peak))
    if not parts:
        raise ValueError('No audible original instruments captured')
    # A single gain retains relative levels in full stems, including sums of
    # key zones. Short auditions are normalized separately for identification.
    gain = min(1.0, 30000 / max(p[2] for p in parts))
    records = []
    for number, (group, pcm, peak) in enumerate(parts, 1):
        filename = f'part-{number:02}.wav'
        write_wav(output/filename, pcm, gain)
        start, excerpt = audition_window(pcm)
        audition = f'part-{number:02}-audition.wav'
        excerpt_gain = 26000 / max(1, int(np.max(np.abs(excerpt))))
        write_wav(output/audition, excerpt, excerpt_gain)
        records.append(dict(part=number, programs=sorted(group['programs']), samples=sorted(group['samples']),
                            file=filename, audition=audition, audition_start_seconds=start/RATE,
                            source_peak=peak, full_stem_gain=gain, audition_gain=excerpt_gain))
    return records


def capture(pack, export, output, seconds=None, port=4380, slot=None):
    report = json.loads(pack.with_suffix('.json').read_text())
    metadata = json.loads((export/'music.json').read_text())
    name = export.name
    index, bank, original = source_bank(pack, report, name)
    if bank['source_sha256'] != metadata['inputs']:
        raise ValueError('Owned export does not match the live pack')
    seconds = seconds if seconds is not None else math.ceil(metadata['sequences'][0]['seconds_one_pass']) + 2
    if not 1 <= seconds <= 120:
        raise ValueError('Use 1..120 seconds')
    frames = round(seconds * RATE)
    if frames * 8 * len(bank['samples']) > 256 * 1024 * 1024:
        raise ValueError('Capture exceeds 256 MiB; choose a shorter window')
    output.mkdir(parents=True, exist_ok=False)
    raw = output/'raw'
    raw.mkdir()
    nav = Navigator(port, timeout=seconds + 15)
    previous = nav.nav('music')['palette']
    try:
        if slot is not None:
            nav.checkpoint('load', slot)
        nav.nav('music', palette=0)
        time.sleep(.5)
        # Independently identify the bank currently loaded in SPU RAM.
        ram = b''.join(bytes.fromhex(nav.call(dict(cmd='spu_ram', addr=i, len=4096))['hex'])
                       for i in range(0, 524288, 4096))
        base = ram.find(original)
        if base < 0:
            raise RuntimeError('The running scene does not contain the requested source bank')
        nav.nav('music-stems', frames=0)
        nav.nav('music-stems', bank=index, frames=frames)
        result = nav.until(lambda: nav.nav('music-stems'), lambda r: not r['active'], 'the original stems')
        if result['frames'] != frames or result['samples'] != len(bank['samples']):
            raise RuntimeError('Stem capture was reset or interrupted')
        nav.nav('music-stems', directory=str(raw.resolve()))
    finally:
        try:
            nav.nav('music-stems', frames=0)
        finally:
            nav.nav('music', palette=previous)
    parts = assemble(output, metadata, bank, frames)
    manifest = dict(bank=name, source_sha256=metadata['inputs'], pack_sha256=report['sha256'],
                    frames=frames, rate=RATE, source_bank_base=base, capture=result, parts=parts,
                    notes=['Original dry voices after native envelopes/panning; no shared reverb or CD input.',
                           'Full stems share one gain; eight-second auditions have independent identification gain.',
                           'Programs sharing source samples are grouped; instrument names await listening.'])
    (output/'stems.json').write_text(json.dumps(manifest, indent=2)+'\n')
    lines = [f'# {name}: original instrument stems', '', *manifest['notes'], '',
             '| Part | Programs | Source samples | Full stem | Short audition |',
             '| --- | --- | --- | --- | --- |']
    for part in parts:
        lines.append(f"| {part['part']} | {part['programs']} | {part['samples']} | "
                     f"[WAV]({part['file']}) | [WAV]({part['audition']}) |")
    (output/'README.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(bank=name, parts=len(parts), seconds=seconds, unmatched=result['unmatched_voice_samples'])))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--export', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float)
    parser.add_argument('--port', type=int, default=4380)
    parser.add_argument('--slot', type=int, choices=range(10))
    args = parser.parse_args()
    capture(args.pack, args.export, args.output, args.seconds, args.port, args.slot)
