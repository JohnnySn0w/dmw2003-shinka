"""Batch original-sample audition stems from owned music_export directories.

No game session or replacement SoundFonts required. MIDI splits preserve source
events; WAVs are an offline approximation, NOT native SPU captures. See manifests
for unsupported playback features. Generated music stays in ignored local output.
"""
import argparse
from collections import Counter, defaultdict, deque
from fractions import Fraction
import hashlib
import html
import json
from pathlib import Path
import struct
import wave

import numpy as np

from capture_music_stems import audition_window, families, write_wav
from music_context import track_context
from music_export import encode_events, midi_events, require

RATE = 44100
LIMITATIONS = [
    'Offline original-sample audition, not a native SPU recording.',
    'Linear sequence pass; custom PS1 controllers/loops, vibrato, portamento, '
    'noise mode, shared reverb and hardware voice stealing are not emulated.',
    'Linear sample interpolation and approximate ADSR/pan/volume; tuning follows '
    'exported root/fine metadata and needs comparison with native playback.',
    'Full stems share headroom per track. Short auditions are independently '
    'normalized for identification, not mix comparison.',
    'Instrument names are unassigned; program numbers are not General MIDI.',
]


def read_score(data):
    require(len(data) >= 22 and data[:4] == b'MThd', 'Missing MIDI header')
    size, fmt, tracks, ppqn = struct.unpack_from('>I3H', data, 4)
    require(size == 6 and fmt == 0 and tracks == 1 and 0 < ppqn < 32768,
            'Expected format-0 PPQN MIDI')
    require(data[14:18] == b'MTrk' and struct.unpack_from('>I', data, 18)[0] == len(data)-22,
            'MIDI track extent mismatch')
    events = midi_events(data[22:])
    timeline = []
    elapsed, tick, tempo = Fraction(0), 0, 500000
    for event in events:
        elapsed += Fraction((event['tick']-tick)*tempo, ppqn*1000000)
        tick = event['tick']
        timeline.append((round(elapsed*RATE), event))
        if event['status'] == 255 and event['meta'] == 0x51:
            tempo = int.from_bytes(bytes(event['data']), 'big')
            require(tempo > 0, 'Zero tempo')
    require(0 < elapsed <= 600, 'Expected a sequence of at most ten minutes')
    return timeline, round(elapsed*RATE)


def split_events(timeline, programs):
    """Keep global/channel controls and only this family's notes, including offs.

    Note-off ownership follows the originating note-on, even after a program
    change. Same-key overlaps use FIFO, shared with the audition renderer.
    """
    selected = [0]*16
    pending = defaultdict(deque)
    result = []
    for frame, event in timeline:
        status, payload = event['status'], event['data']
        channel, kind = status & 15, status & 0xf0
        keep = True
        if kind == 0xc0:
            selected[channel] = payload[0]
        elif kind == 0x90 and payload[1]:
            keep = selected[channel] in programs
            pending[channel, payload[0]].append(keep)
        elif kind == 0x80 or (kind == 0x90 and not payload[1]):
            queue = pending[channel, payload[0]]
            keep = queue.popleft() if queue else False
        if keep:
            result.append((frame, event))
    return result


def envelope_times(tone):
    """Approximate the register rates as continuous ramps, not SPU steps."""
    def duration(speed, decreasing=False):
        increment = (8 if decreasing else 7) - (speed & 3)
        increment *= 2**max(0, (47-speed)//4)
        interval = 2**max(0, (speed-44)//4)
        return min(30., max(1/RATE, 32767*interval/increment/RATE))
    a, b = tone['adsr1'], tone['adsr2']
    attack = duration((a >> 8) & 127) * (1.75 if a & 0x8000 else 1)
    decay = duration(((a >> 4) & 15)*4, True)
    sustain = min(1., ((a & 15)+1)/16)
    release = duration((b & 31)*4, True)
    sustain_time = duration((b >> 6) & 127, bool(b & 0x4000))
    return attack, decay, sustain, release, sustain_time


class OriginalSynth:
    def __init__(self, bank, samples):
        self.bank, self.samples = bank, samples
        self.programs = {p['program']: p for p in bank['programs']}
        self.controls = [dict(program=0, volume=1., expression=1., pan=64,
                              bend=0., sustain=False) for _ in range(16)]
        self.voices = []
        self.serial = 0
        self.unsupported = Counter()

    def event(self, event):
        status, data = event['status'], event['data']
        ch, kind = status & 15, status & 0xf0
        c = self.controls[ch]
        if status >= 240:
            if status != 255:
                self.unsupported[f'system-{status:02x}'] += 1
            return
        if kind == 0xc0:
            c['program'] = data[0]
        elif kind == 0x90 and data[1]:
            require(c['program'] in self.programs, 'Note uses an absent VAB program')
            p = self.programs[c['program']]
            tones = [t for t in p['tones'] if t['key_min'] <= data[0] <= t['key_max']]
            if not tones:
                self.unsupported[f'unmapped-key-program-{c["program"]}-key-{data[0]}'] += 1
                return  # No declared source: report the missing note, never invent a route.
            self.serial += 1
            for t in tones:
                self.voices.append(dict(ch=ch, key=data[0], velocity=data[1]/127,
                                        program=p, tone=t, age=0, position=0.,
                                        released=None, level=0., held=True, serial=self.serial))
        elif kind == 0x80 or (kind == 0x90 and not data[1]):
            matches = [v for v in self.voices if v['ch'] == ch and v['key'] == data[0] and v['held']]
            if matches:
                first = min(v['serial'] for v in matches)
                for v in matches:
                    if v['serial'] == first:
                        v['held'] = False
                        if not c['sustain']:
                            self.release(v)
        elif kind == 0xe0:
            c['bend'] = ((data[0] | data[1] << 7)-8192)/8192
        elif kind == 0xb0:
            cc, value = data
            if cc in (7, 11):
                c['volume' if cc == 7 else 'expression'] = value/127
            elif cc == 10:
                c['pan'] = value
            elif cc == 64:
                c['sustain'] = value >= 64
                if not c['sustain']:
                    for v in self.voices:
                        if v['ch'] == ch and not v['held']:
                            self.release(v)
            elif cc == 120:
                self.voices = [v for v in self.voices if v['ch'] != ch]
            elif cc == 123:
                for v in self.voices:
                    if v['ch'] == ch:
                        v['held'] = False
                        if not c['sustain']:
                            self.release(v)
            elif cc == 121:
                c.update(expression=1., bend=0., sustain=False)
                for v in self.voices:
                    if v['ch'] == ch and not v['held']:
                        self.release(v)
            else:
                self.unsupported[f'CC{cc}'] += 1
        else:
            self.unsupported[f'status-{kind:02x}'] += 1

    @staticmethod
    def amp(v, age):
        a, d, s, r, st = envelope_times(v['tone'])
        if v['released'] is not None:
            return v['level'] * np.maximum(0., 1-(age-v['released']/RATE)/r)
        sustain = np.clip(s + (-1 if v['tone']['adsr2'] & 0x4000 else 1)
                          * np.maximum(0, age-a-d)/st, 0, 1)
        return np.where(age < a, age/a, np.where(age < a+d, 1-(1-s)*(age-a)/d, sustain))

    def release(self, v):
        if v['released'] is None:
            v['level'] = float(self.amp(v, v['age']/RATE))
            v['released'] = v['age']

    def render(self, frames):
        output = np.zeros((frames, 2), dtype=np.float32)
        offsets = np.arange(frames)
        keep = []
        for v in self.voices:
            t, p, c = v['tone'], v['program'], self.controls[v['ch']]
            sample, loop = self.samples[t['sample']]
            bend_range = t['pitch_bend_up' if c['bend'] >= 0 else 'pitch_bend_down']
            step = 2**((v['key'] + c['bend']*bend_range - t['root_key']-t['fine_tuning']/128)/12)
            positions = v['position'] + offsets*step
            if loop:
                positions = np.where(positions >= loop[1],
                                     loop[0]+(positions-loop[0]) % (loop[1]-loop[0]), positions)
            indices = np.floor(positions).astype(np.int64)
            fraction = positions-indices
            following = indices+1
            if loop:
                following = np.where(following >= loop[1], loop[0], following)
            left = sample[np.clip(indices, 0, len(sample)-1)]
            right = np.where(following < len(sample), sample[np.clip(following, 0, len(sample)-1)], 0.)
            signal = np.where(indices < len(sample), left*(1-fraction)+right*fraction, 0.)
            signal *= self.amp(v, (v['age']+offsets)/RATE)
            signal *= v['velocity']*c['volume']*c['expression']*p['volume']/127*t['volume']/127
            signal *= self.bank['master_volume']/127
            pan = np.clip((c['pan']+p['pan']+t['pan']+self.bank['master_pan']-3*64)/127, 0, 1)
            output[:, 0] += signal*(1-pan)
            output[:, 1] += signal*pan
            v['position'] += frames*step
            if loop and v['position'] >= loop[1]:
                v['position'] = loop[0]+(v['position']-loop[0]) % (loop[1]-loop[0])
            v['age'] += frames
            alive = loop or v['position'] < len(sample)
            if alive and (v['released'] is None or self.amp(v, v['age']/RATE) > 0):
                keep.append(v)
        self.voices = keep
        return output


def render(timeline, frames, bank, samples):
    synth = OriginalSynth(bank, samples)
    audio = np.zeros((frames+RATE*2, 2), dtype=np.float32)
    position = 0
    def advance(end):
        nonlocal position
        while position < end:
            count = min(4096, end-position)
            audio[position:position+count] = synth.render(count)
            position += count
    for frame, event in timeline:
        advance(frame)
        synth.event(event)
    advance(frames)
    for v in synth.voices:
        synth.release(v)
    advance(len(audio))
    audio[-1102:] *= np.linspace(1, 0, 1102)[:, None]
    require(np.all(np.isfinite(audio)), 'Non-finite audition audio')
    return audio, dict(synth.unsupported)


def load_samples(export, bank):
    result, hashes = {}, {}
    for row in bank['samples']:
        path = export/row['wav']
        require(path.resolve().parent == export.resolve(), 'Sample path escapes export')
        hashes[row['wav']] = hashlib.sha256(path.read_bytes()).hexdigest()
        with wave.open(str(path)) as f:
            require(f.getnchannels() == 1 and f.getsampwidth() == 2 and f.getframerate() == RATE,
                    'Expected mono 16-bit 44100 Hz exported samples')
            pcm = np.frombuffer(f.readframes(f.getnframes()), dtype='<i2').astype(np.float32)
        require(len(pcm) == row['frames'] and len(pcm) > 0, 'Sample frame count mismatch')
        loop = row['loop_frames']
        require(not loop or 0 <= loop[0] < loop[1] <= len(pcm), 'Invalid sample loop')
        result[row['id']] = pcm, loop
    return result, hashes


def split_track(export, metadata, sequence, output):
    source = export/f'sequence-{sequence["id"]:03}.mid'
    data = source.read_bytes()
    timeline, frames = read_score(data)
    bank = metadata['bank']
    samples, hashes = load_samples(export, bank)
    used = {p['program'] for p in sequence['program_usage'] if p['notes']}
    require(not sequence['unmapped_programs'], 'Sequence references external programs')
    grouped = families(dict(bank=dict(programs=[p for p in bank['programs'] if p['program'] in used])),
                       set(samples))
    output.mkdir(parents=True, exist_ok=False)
    records, max_peak = [], 0.
    for number, group in enumerate(grouped, 1):
        events = split_events(timeline, group['programs'])
        audio, ignored = render(events, frames, bank, samples)
        peak = float(np.max(np.abs(audio)))
        require(peak > 0, 'Silent family; inspect source routing')
        prefix = f'part-{number:02}'
        # Spool one family at a time; memory does not scale with OST size.
        np.save(output/f'{prefix}.npy', audio)
        body = encode_events([e for _, e in events])
        (output/f'{prefix}.mid').write_bytes(data[:18]+struct.pack('>I', len(body))+body)
        max_peak = max(max_peak, peak)
        records.append(dict(part=number, programs=sorted(group['programs']), samples=sorted(group['samples']),
                            file=f'{prefix}.wav', midi=f'{prefix}.mid', audition=f'{prefix}-audition.wav',
                            raw_peak=peak, ignored_events=ignored))
    require(records, 'No instrument families')
    gain = min(1., 30000/max_peak)
    for part in records:
        temp = output/Path(part['file']).with_suffix('.npy')
        audio = np.load(temp)
        write_wav(output/part['file'], audio, gain)
        start, excerpt = audition_window(audio)
        excerpt_gain = 26000/float(np.max(np.abs(excerpt)))
        write_wav(output/part['audition'], excerpt, excerpt_gain)
        part.update(full_stem_gain=gain, audition_gain=excerpt_gain, audition_start_seconds=start/RATE)
        temp.unlink()  # only the exact spool file created above
    midi_hash = hashlib.sha256(data).hexdigest()
    manifest = dict(renderer='offline-original-sample-approximation-v1', bank=export.name,
                    sequence=sequence['id'], source_sha256=metadata['inputs'], midi_sha256=midi_hash,
                    sample_sha256=hashes, metadata_sha256=hashlib.sha256((export/'music.json').read_bytes()).hexdigest(),
                    rate=RATE, frames=frames+RATE*2, context=track_context(midi_hash),
                    parts=records, limitations=LIMITATIONS)
    (output/'stems.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    return manifest


def write_index(output, report):
    sections = ['<!doctype html><meta charset="utf-8"><title>Shinka instrument auditions</title>',
                '<style>body{background:#101624;color:#e4edff;font:17px system-ui;max-width:1000px;'
                'margin:3rem auto;padding:1rem}a{color:#76bfff}article{border-top:1px solid #456;'
                'padding:1rem 0}audio{width:100%}summary{cursor:pointer;padding:1rem}</style>',
                '<h1>Original instrument auditions</h1><p>Offline approximations, not native captures. '
                'Short clips are normalized individually. Full WAVs share gain within each track.</p>']
    for track in report['tracks']:
        context = track['manifest'].get('context') or {}
        title = html.escape(context.get('title', track['id']))
        sections.append(f'<details><summary>{title} · {html.escape(track["id"])}</summary>')
        sections.append(f'<p>{html.escape(context.get("scene", "Scene unverified"))}</p>')
        for part in track['manifest']['parts']:
            base = track['id']+'/'
            sections.append(f'<article><b>Part {part["part"]}</b> · Programs {part["programs"]} '
                            f'· Samples {part["samples"]}<audio controls preload="none" '
                            f'src="{base+part["audition"]}"></audio>'
                            f'<a href="{base+part["file"]}">Full stem</a> · '
                            f'<a href="{base+part["midi"]}">MIDI</a></article>')
            if part['ignored_events']:
                sections.append('<details><summary>Unrendered events in this part</summary><pre>'+
                                html.escape(json.dumps(part['ignored_events'], indent=2))+'</pre></details>')
        sections.append('</details>')
    sections.append('<h2>Playback limits</h2><ul>'+''.join(f'<li>{html.escape(x)}</li>' for x in LIMITATIONS)+'</ul>')
    sections.append(f'<p>{len(report["skipped"])} skipped cues/sequences; {len(report["errors"])} failures. '
                    'See batch.json for the complete accounting.</p>')
    (output/'index.html').write_text('\n'.join(sections), encoding='utf-8')
    (output/'batch.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


def batch(exports, output, banks=None):
    require(not output.exists(), 'Choose a new output directory')
    candidates = sorted(exports.glob('*/music.json'))
    require(candidates, 'No exported banks found')
    if banks:
        require(set(banks) <= {p.parent.name for p in candidates}, 'Requested bank is absent')
        candidates = [p for p in candidates if p.parent.name in banks]
    output.mkdir(parents=True)
    report = dict(tracks=[], skipped=[], errors=[], limitations=LIMITATIONS)
    for path in candidates:
        try:
            metadata = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            report['errors'].append(dict(id=path.parent.name, reason=str(exc)))
            continue
        for seq in metadata['sequences']:
            identity = f'{path.parent.name}-{seq["id"]:03}'
            if seq['seconds_one_pass'] < 1 or seq['unmapped_programs'] or not seq['program_usage']:
                report['skipped'].append(dict(id=identity, seconds=seq['seconds_one_pass'],
                                             reason='Short/nonmusical cue or external/unmapped program',
                                             unmapped_programs=seq['unmapped_programs']))
                continue
            try:
                manifest = split_track(path.parent, metadata, seq, output/identity)
                report['tracks'].append(dict(id=identity, manifest=manifest))
                print(f'{identity}: {len(manifest["parts"])} parts', flush=True)
            except (ValueError, OSError, KeyError, wave.Error, EOFError) as exc:
                reason = f'{type(exc).__name__}: {exc}'
                report['errors'].append(dict(id=identity, reason=reason))
                print(f'{identity}: FAILED: {reason}', flush=True)
            write_index(output, report)
    write_index(output, report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exports', type=Path, default=Path('output/music-catalog-export'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bank', action='append', help='Optional bank filter; repeatable')
    args = parser.parse_args()
    result = batch(args.exports, args.output, args.bank)
    print(f'{len(result["tracks"])} tracks, {len(result["skipped"])} skipped, {len(result["errors"])} failures')
    raise SystemExit(1 if result['errors'] else 0)
