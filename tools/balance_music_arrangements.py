"""Make conservative, reference-guided local auditions without replacing originals.

The spectral K-weighted measurements are a windowed loudness proxy, NOT a
standards-conformant LUFS meter. References are offline original-sample renders.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import wave
import zipfile

import numpy as np

RATE = 48000
PALETTES = ('sampled', 'ds', 'chip')
WINDOW = 19200
HOP = 9600


def decode(path, filters=None):
    command = ['ffmpeg', '-v', 'error', '-threads', '1', '-i', str(path)]
    if filters:
        command += ['-af', filters]
    raw = subprocess.check_output(command + ['-f', 'f32le', '-ac', '2', '-ar', str(RATE), '-'])
    audio = np.frombuffer(raw, dtype='<f4').reshape(-1, 2).copy()
    if not len(audio) or not np.isfinite(audio).all():
        raise ValueError(f'Invalid audio: {path}')
    return audio


def spectrum(audio):
    """Per-block stereo power; 400 ms Hann windows, 200 ms hop."""
    if len(audio) < WINDOW:
        audio = np.pad(audio, ((0, WINDOW-len(audio)), (0, 0)))
    window = np.hanning(WINDOW)
    normalization = WINDOW * np.sum(window**2)
    powers = []
    for start in range(0, len(audio)-WINDOW+1, HOP):
        fft = np.fft.rfft(audio[start:start+WINDOW] * window[:, None], axis=0)
        power = np.sum(np.abs(fft)**2, axis=1) / normalization
        power[1:-1] *= 2
        powers.append(power)
    return np.asarray(powers)


def k_curve():
    # BS.1770-4's two 48 kHz filter responses, applied in the frequency domain.
    z = np.exp(-2j*np.pi*np.fft.rfftfreq(WINDOW))
    shelf = (1.53512485958697-2.69169618940638*z+1.19839281085285*z*z) / (
        1-1.69065929318241*z+.73248077421585*z*z)
    highpass = (1-2*z+z*z) / (1-1.99004745483398*z+.99007225036621*z*z)
    return np.abs(shelf*highpass)**2


K_CURVE = k_curve()
FREQUENCIES = np.fft.rfftfreq(WINDOW, 1/RATE)


def active_mask(power):
    energy = power @ K_CURVE
    return energy > max(float(energy.max()) * 10**(-35/10), 1e-10)


def measure(power, mask=None):
    mask = active_mask(power) if mask is None else mask
    if len(mask) != len(power):
        raise ValueError('Reference and arrangement durations differ')
    if not np.any(mask):
        return dict(db=-100., warmth=-100., presence=-100., active_blocks=0)
    average = np.mean(power[mask], axis=0)
    total = max(float(np.sum(average)), 1e-20)
    bands = {}
    for name, low, high in [('warmth', 150, 600), ('presence', 1500, 5000)]:
        fraction = float(np.sum(average[(FREQUENCIES >= low) & (FREQUENCIES < high)])) / total
        bands[name] = float(10*np.log10(max(fraction, 1e-10)))
    return dict(db=float(-.691+10*np.log10(max(float(average @ K_CURVE), 1e-20))),
                active_blocks=int(np.sum(mask)), **bands)


def eq_settings(reference, current, voice):
    if voice == 'original' or not reference['active_blocks'] or not current['active_blocks']:
        return dict(warmth=0., presence=0.)
    # Only nudge the broad spectral envelope. Never synthesize a missing band.
    limit = 1. if voice.startswith('drum') or voice in ('kit', 'triangle', 'bell') else 2.
    return {key: round(float(np.clip((reference[key]-current[key])*.25, -limit, limit)), 2)
            if min(reference[key], current[key]) > -35 else 0.
            for key in ('warmth', 'presence')}


def write_wav(path, audio):
    if not np.isfinite(audio).all() or np.max(np.abs(audio)) > 1:
        raise ValueError('Nonfinite or clipping audio')
    with wave.open(str(path), 'wb') as stream:
        stream.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
        stream.writeframes(np.rint(audio*32767).astype('<i2').tobytes())


def peak_gain(audio, target_db=-20):
    measured = measure(spectrum(audio))['db']
    return min(10**((target_db-measured)/20), .79/max(float(np.max(np.abs(audio))), 1e-12))


def balance_track(track, manifest, library, listening, destination):
    if (track['source_sha256'] != manifest['source_sha256']
            or track['midi_sha256'] != manifest['midi_sha256']):
        raise ValueError(f"Reference identity changed: {track['id']}")
    result = {key: track[key] for key in ('id', 'title', 'scene', 'source_sha256', 'midi_sha256')}
    result['palettes'] = {}
    refs = {}
    for part in track['parts']:
        source = next(p for p in manifest['parts'] if p['part'] == part['part'])
        if source['programs'] != part['programs']:
            raise ValueError('Reference program mapping changed')
        power = spectrum(decode(library/track['id']/source['file']))
        mask = active_mask(power)
        refs[part['part']] = (measure(power, mask), mask)
    folder = destination/track['id']
    folder.mkdir(parents=True, exist_ok=True)
    for palette in PALETTES:
        stems, records = [], []
        for part in track['parts']:
            number = part['part']
            reference, mask = refs[number]
            source = listening/track['id']/f'{palette}-part-{number:02}.flac'
            audio = decode(source)
            before = measure(spectrum(audio), mask)
            eq = eq_settings(reference, before, part['voice'])
            if any(eq.values()):
                audio = decode(source, f"equalizer=f=300:t=q:w=0.7:g={eq['warmth']},"
                                       f"equalizer=f=2500:t=q:w=0.7:g={eq['presence']}")
            after_eq = measure(spectrum(audio), mask)
            # Keep original part hierarchy, using the original set's common trim.
            target = reference['db'] + 20*np.log10(track['common_gain'])
            gain_db = float(np.clip(target-after_eq['db'], -6, 6)) if reference['active_blocks'] else 0.
            if part['voice'] == 'original':
                gain_db = 0.
            audio *= 10**(gain_db/20)
            stems.append(audio)
            records.append(dict(part=number, instrument=part['label']['instrument'],
                                voice=part['voice'], gain_db=round(gain_db, 3), **eq,
                                before=before, reference=reference,
                                file=f"balanced/{track['id']}/{palette}-part-{number:02}.flac"))
        if len({len(s) for s in stems}) != 1:
            raise ValueError('Unaligned stems')
        mix = np.sum(stems, axis=0)
        gain = peak_gain(mix)
        # Individual stems must also fit PCM: cancellation can hide a loud stem.
        gain = min(gain, .95/max(float(np.max(np.abs(s))) for s in stems))
        mix *= gain
        write_wav(folder/f'{palette}.wav', mix)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(folder/f'{palette}.wav'),
                        '-codec:a', 'libmp3lame', '-q:a', '2', str(folder/f'{palette}.mp3')], check=True)
        for stem, record in zip(stems, records):
            raw = (stem*gain).astype('<f4').tobytes()
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(RATE),
                            '-ac', '2', '-i', '-', '-c:a', 'flac',
                            str(listening/record['file'])], input=raw, check=True)
        original = decode(listening/track['id']/f'{palette}.wav')
        compare_db = measure(spectrum(mix))['db']-measure(spectrum(original))['db']
        # Listening comparison only attenuates; never clips an original mix.
        result['palettes'][palette] = dict(parts=records, master_gain=gain,
            measured_db=measure(spectrum(mix))['db'], sample_peak=float(np.max(np.abs(mix))),
            seconds=len(mix)/RATE, compare_original_gain=min(1., 10**(compare_db/20)),
            compare_balanced_gain=min(1., 10**(-compare_db/20)),
            mix=f"balanced/{track['id']}/{palette}.mp3")
        print(f"Balanced {track['id']} {palette}", flush=True)
    (folder/'balance.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result


def package_previews(listening, catalog):
    """Package generated previews only; never include labels or game inputs."""
    target = listening/'balanced/Shinka-balanced-listening-samples.zip'
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_STORED) as archive:
        for track in catalog['tracks']:
            for palette, data in track['palettes'].items():
                archive.write(listening/data['mix'], f"{track['id']}/{palette}.mp3")
        archive.writestr('README.txt', 'Shinka balance auditions: Sampled, DS, Chip.\n'
                         'Reference-guided suggestions, not final masters.\n'
                         'These previews do not include personal mix-desk slider adjustments.\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('listening', type=Path)
    parser.add_argument('--library', type=Path, default=Path('output/music-ost-split-03'))
    parser.add_argument('--track', action='append')
    args = parser.parse_args()
    report = json.loads((args.listening/'arrangements.json').read_text(encoding='utf-8'))
    batch = json.loads((args.library/'batch.json').read_text(encoding='utf-8'))
    manifests = {t['id']: t['manifest'] for t in batch['tracks']}
    destination = args.listening/'balanced'
    if (destination/'catalog.json').exists():
        parser.error('Preserving an existing balance catalog; use a fresh arrangement folder')
    destination.mkdir(exist_ok=True)
    tracks = []
    for track in report['tracks']:
        if args.track and track['id'] not in args.track:
            continue
        saved = destination/track['id']/'balance.json'
        if saved.exists():
            raise ValueError(f'Preserving existing balance: {saved}')
        tracks.append(balance_track(track, manifests[track['id']], args.library,
                                    args.listening, destination))
    catalog = dict(schema_version=1, method='active-window K-weighted spectral proxy v1', tracks=tracks)
    catalog['identity'] = hashlib.sha256(json.dumps(catalog, sort_keys=True).encode()).hexdigest()
    (destination/'catalog.json').write_text(json.dumps(catalog, indent=2)+'\n', encoding='utf-8')
    package_previews(args.listening, catalog)


if __name__ == '__main__':
    main()
