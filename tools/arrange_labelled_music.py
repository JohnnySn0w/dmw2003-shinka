"""Render identity-checked notebook labels into local three-palette auditions.

Uses an explicitly prepared CC0 sample catalog. Never alters the label notebook
or live game pack. Source music, labels and rendered audio stay under output/.
"""
import argparse
import copy
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import wave

import numpy as np

from label_music_stems import family_identity, identity_key
from music_ds import room_mix
from split_music_ost import OriginalSynth, RATE, read_score, split_events


def read_audio(path):
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path),
                                   '-f', 'f32le', '-ac', '1', '-ar', str(RATE), '-'])
    return np.frombuffer(raw, dtype='<f4').copy()


def write_audio(path, audio):
    if not np.isfinite(audio).all() or np.max(np.abs(audio)) > 1:
        raise ValueError(f'Invalid output levels: {path}')
    with wave.open(str(path), 'wb') as f:
        f.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
        f.writeframes(np.rint(audio * 32767).astype('<i2').tobytes())


def rms(audio):
    return float(np.sqrt(np.mean(audio.astype(np.float64)**2)))


def route(label):
    """Audition interpretations, kept separate from the listener's own words."""
    name = label['instrument'].lower()
    notes = label.get('notes', '').lower()
    exact = {
        'piano': 'piano', 'grand piano': 'piano', 'bass guitar': 'bass', 'electric bass': 'bass',
        'flute': 'flute', 'piccolo': 'piccolo', 'ney': 'flute', 'clarinet': 'clarinet',
        'violin': 'violin', 'violins': 'violin', 'viola': 'viola',
        'string-like synth, possibly violin': 'violin', 'plucked violin': 'pizzicato',
        'cello (plucked)': 'cello-pizz', 'tuba': 'tuba', 'trumpet': 'trumpet',
        'trumpets': 'trumpet', 'brass instrument': 'trombone', 'french horn': 'horn', 'horn': 'horn',
        'accordion': 'accordion', 'bandoneon': 'accordion', 'concertina': 'accordion',
        'harpsicord': 'harpsichord', 'harp': 'harp', 'santur': 'psaltery', 'kanun': 'zither',
        'sitar': 'zither', 'surbahar': 'zither', 'banjo': 'pluck',
        'exotic string instrument with good sustain after a pluck': 'pluck',
        'marimba': 'marimba', 'wood xylophone': 'xylophone', 'xylophone': 'xylophone',
        'bell': 'bell', 'glockenspiel': 'bell', 'hand bells': 'chimes', 'celesta': 'bell',
        'metal triangle': 'triangle', 'kalimba': 'kalimba', 'gong': 'gong', 'cajón': 'cajon',
        'bongo': 'bongo', 'hi hat': 'drum-hat', 'cymbals': 'drum-cymbal',
        'hammering metal': 'anvil', 'steel drum': 'metal', 'metal drum': 'metal',
        'metal flute': 'metal-flute', 'glass harmonica': 'glass', 'timpani': 'timpani',
        'spanish guitar': 'nylon', 'guitar': 'guitar', 'electric guitar': 'guitar',
        'organ': 'organ-synth', 'organ piano': 'organ-synth', 'organ w/ flute stops': 'organ-synth',
        'calliope': 'organ-synth', 'calliaphone': 'organ-synth',
        'mouth harp': 'jaw-synth', 'slide whistle': 'whistle', 'laser': 'laser',
        'piano synth': 'fm-piano', 'synth piano': 'fm-piano', 'synth': 'synth',
        'beepy synth': 'synth', 'beeps and boops': 'synth',
        'sfx': 'original', 'electrical sparks': 'original',
    }
    if 'drum kit' in name:
        voice = 'kit'
    elif 'electric guitar' in name:
        voice = 'distorted' if ('distort' in name+notes or 'fuzz' in notes or 'pedal' in name+notes) else 'guitar'
    elif 'bass guitar' in name:
        voice = 'bass'
    else:
        if name not in exact:
            raise ValueError(f'Unreviewed instrument label: {name}')
        voice = exact[name]
    if (voice in ('synth', 'fm-piano') and ('violin' in notes or 'strings' in notes)
            and 'not the actual string' not in notes):
        voice = 'violin'
    if voice == 'synth' and 'timpani' in notes:
        voice = 'timpani'
    if voice == 'synth' and 'tongue drum' in notes:
        voice = 'metal'
    return voice


def wave_sample(kind, root=60):
    t = np.arange(RATE * 3) / RATE
    f = 440 * 2**((root-69)/12)
    phase = 2*np.pi*f*t
    if kind == 'timpani':
        a = sum(np.sin(phase * ratio) * np.exp(-t*decay)*gain
                for ratio, decay, gain in [(1, 2.8, 1), (1.5, 4, .45), (2.05, 7, .2)])
    elif kind in ('metal', 'metal-flute'):
        a = np.sin(phase)*np.exp(-t*2) + .4*np.sin(phase*2.76)*np.exp(-t*5)
        if kind == 'metal-flute':
            a += .7*np.sin(phase)
    elif kind == 'laser':
        a = np.sin(phase + 60*np.exp(-t*12))*np.exp(-t*9)
    elif kind == 'whistle':
        a = np.sin(phase)
    elif kind == 'organ-synth':
        a = np.sin(phase)+.5*np.sin(phase*2)+.25*np.sin(phase*3)+.15*np.sin(phase*4)
    elif kind == 'jaw-synth':
        a = np.sin(phase + 2*np.sin(phase*.5))*np.exp(-t*4)
    elif kind == 'triangle':
        a = 2/np.pi*np.arcsin(np.sin(phase))
    elif kind == 'pulse':
        a = sum(np.sin(phase*n)/n for n in (1, 3, 5, 7, 9))
    else:
        a = np.sin(phase + 1.2*np.exp(-t*6)*np.sin(phase*2))
    return a.astype(np.float32)


class Library:
    def __init__(self, directory):
        self.directory = directory
        self.catalog = json.loads((directory/'catalog.json').read_text())
        self.cache = {}
        self.raw_cache = {}
        self.sf = None

    def raw(self, path):
        path = Path(path)
        if path not in self.raw_cache:
            self.raw_cache[path] = read_audio(path)
        return self.raw_cache[path]

    def get(self, voice, key, palette):
        # Cache waveforms by the actual multisample, not by every MIDI key.
        oneshot = voice.startswith('drum-') or voice in ('bongo', 'cajon', 'gong', 'triangle', 'anvil')
        rows = [p for p in self.catalog if p['instrument']==voice]
        if palette=='chip' or oneshot:
            key = 60
        elif voice in ('piano', 'bass', 'clarinet', 'guitar', 'nylon', 'distorted'):
            key = min(84, max(36, round(key/12)*12))
            if voice=='bass':
                key = min(48, key)
            elif voice=='clarinet':
                key = min(72, max(60, key))
            elif voice in ('guitar', 'nylon', 'distorted'):
                key = min(72, max(48, key))
        elif rows:
            key = min(rows, key=lambda p: abs(p['root']-key))['root']
        elif voice!='accordion':
            key = 60
        cache_key = (voice, key, palette)
        if cache_key in self.cache:
            return self.cache[cache_key]
        sustain = voice in ('violin', 'viola', 'trumpet', 'tuba', 'trombone', 'horn', 'flute',
                            'piccolo', 'clarinet', 'accordion', 'organ-synth', 'synth', 'whistle', 'glass')
        root = key if oneshot else 60
        source = None
        if palette == 'chip':
            if oneshot:
                t = np.arange(RATE)/RATE
                rng = np.random.default_rng(127+key)
                a = rng.uniform(-1, 1, len(t))*np.exp(-t*(20 if voice=='drum-hat' else 7))
                if voice in ('drum-kick', 'drum-tom', 'bongo', 'cajon'):
                    a = np.sin(2*np.pi*(65*t+6*(1-np.exp(-t*20))))*np.exp(-t*12)
            else:
                kind = 'triangle' if voice in ('bass', 'flute', 'piccolo', 'timpani') else 'pulse'
                if voice in ('bell', 'chimes', 'metal', 'kalimba', 'marimba'):
                    kind = 'metal'
                a = wave_sample(kind, root)
                sustain = True
            source = 'Procedural chip voice'
        elif voice in ('piano', 'bass', 'clarinet', 'guitar', 'nylon', 'distorted'):
            if self.sf is None:
                from tinysoundfont import Synth
                self.sf = Synth(gain=-6, samplerate=RATE)
                self.sfids = {}
            base = 'guitar' if voice == 'distorted' else voice
            if base not in self.sfids:
                path = (next((self.directory/base).rglob('*.sf2')) if base in ('guitar', 'nylon')
                        else Path('output/music-banks')/(base+'.sf2'))
                sid = self.sf.sfload(path.read_bytes())
                presets = [i for i in range(128) if self.sf.sfpreset_name(sid, 0, i)]
                if not presets:
                    raise ValueError(f'Missing preset in {path}')
                self.sfids[base] = sid, presets[0]
            sid, preset = self.sfids[base]
            root = min(84, max(36, round(key/12)*12))
            sfkey = (base, root)
            if sfkey not in self.raw_cache:
                self.sf.sounds_off()
                self.sf.program_select(0, sid, 0, preset, is_drums=False)
                self.sf.noteon(0, root, 100)
                self.raw_cache[sfkey] = np.frombuffer(self.sf.generate_simple(RATE*3), dtype=np.float32).reshape(-1, 2).mean(axis=1)
            a = self.raw_cache[sfkey]
            if voice == 'distorted':
                a = np.tanh(a*8)
            source = f'FreePats CC0 {base}'
        elif voice == 'accordion':
            sfz = next((self.directory/'accordion').rglob('*.sfz'))
            entries = re.findall(r'<region> sample=(.*?) pitch_keycenter=(\d+).*?tune=(-?\d+)\s+loop_start=(\d+) loop_end=(\d+)', sfz.read_text())
            filename, note, tune, _, _ = min(entries, key=lambda e: abs(int(e[1])-key))
            a = self.raw(sfz.parent/filename)
            root = int(note)-int(tune)/100
            source = 'FreePats CC0 Button Accordion HN'
        else:
            rows = [p for p in self.catalog if p['instrument']==voice]
            if rows:
                row = min(rows, key=lambda p: abs(p['root']-key))
                path = self.directory/row['file']
                if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
                    raise ValueError(f'Changed instrument source: {path}')
                a = self.raw(path)
                root = row['root'] if row['pitched'] else key
                source = row['repo']+'/'+row['path']
            else:
                a = wave_sample(voice, root)
                source = f'Procedural approximation: {voice}'
        # Trim only onset silence; raw orchestral recordings can contain pre-roll.
        active = np.flatnonzero(np.abs(a)>max(1e-6, np.max(np.abs(a))*.005))
        if not len(active):
            raise ValueError(f'Silent instrument {voice}')
        a = a[max(0, active[0]-44):].copy()
        a -= np.mean(a)
        a /= max(float(np.max(np.abs(a))), 1e-6)
        a[:min(88, len(a))] *= np.linspace(0, 1, min(88, len(a)))
        loop = None
        if sustain and len(a)>RATE//2:
            # Use a stable middle section, not the recorded note-off tail.
            end = min(len(a), int(RATE*1.5))
            start = min(int(RATE*.4), end//3)
            fade = min(1024, (end-start)//4)
            a[end-fade:end] = a[end-fade:end]*np.linspace(1, 0, fade)+a[start-fade:start]*np.linspace(0, 1, fade)
            loop = (start, end)
        if palette == 'ds':
            # Sample-rate/bit-depth color, with a bright 12 kHz bus later.
            at = np.arange(0, len(a), RATE/32768)
            low = np.interp(at, np.arange(len(a)), a)
            a = np.interp(np.arange(len(a)), at, np.round(low*2047)/2047).astype(np.float32)
        result = a.astype(np.float32), loop, root, source
        self.cache[cache_key] = result
        return result


class AuditionSynth(OriginalSynth):
    @staticmethod
    def amp(v, age):
        tone = v['tone']
        attack, release = tone.get('attack', .004), tone.get('release', .15)
        if v['released'] is not None:
            return v['level']*np.maximum(0, 1-(age-v['released']/RATE)/release)
        return np.minimum(1, age/attack)


def kit_voice(key, label):
    if 'indian' in label['instrument'].lower():
        return 'bongo' if key % 2 else 'cajon'
    if key in (35, 36):
        return 'drum-kick'
    if key in (37, 38, 39, 40):
        return 'drum-snare'
    if key in (42, 44, 46, 54, 69, 70):
        return 'drum-hat'
    if key in (49, 51, 52, 55, 57, 59):
        return 'drum-cymbal'
    return 'drum-tom'


def render_part(timeline, frames, bank, programs, label, palette, library):
    voice = route(label)
    new_bank = copy.deepcopy(bank)
    samples, sources = {}, set()
    sid = 0
    for p in new_bank['programs']:
        if p['program'] not in programs:
            continue
        tones = []
        for key in range(128):
            original = next((t for t in p['tones'] if t['key_min']<=key<=t['key_max']), None)
            if original is None:
                continue
            chosen = kit_voice(key, label) if voice=='kit' else voice
            a, loop, root, source = library.get(chosen, key, palette)
            if chosen.startswith('drum-') or chosen in ('bongo', 'cajon', 'gong', 'triangle', 'anvil'):
                root = key
            sources.add(source)
            sid += 1
            samples[sid] = a, loop
            tone = dict(original, sample=sid, root_key=root, fine_tuning=0,
                        key_min=key, key_max=key, volume=110, attack=.005,
                        release=.22 if voice in ('harp', 'piano', 'bell', 'chimes') else .12)
            if voice in ('violin', 'viola', 'accordion', 'horn'):
                tone['attack'] = .025
            tones.append(tone)
        p['tones'] = tones
    synth = AuditionSynth(new_bank, samples)
    out = np.zeros((frames+2*RATE, 2), dtype=np.float32)
    pos = 0
    def advance(end):
        nonlocal pos
        while pos<end:
            count = min(4096, end-pos)
            out[pos:pos+count] = synth.render(count)
            pos += count
    for frame, event in timeline:
        advance(frame)
        synth.event(event)
    advance(frames)
    for v in synth.voices:
        synth.release(v)
    advance(len(out))
    return out, sorted(sources), dict(synth.unsupported)


def completed_tracks(batch, labels):
    complete, skipped = [], []
    for row in batch['tracks']:
        m = row['manifest']
        entries = [labels.get(identity_key(family_identity(m, p))) for p in m['parts']]
        if not entries or not all(x and x.get('instrument', '').strip() for x in entries):
            skipped.append(dict(id=row['id'], reason='Not all instrument families labeled'))
            continue
        for p, label in zip(m['parts'], entries):
            if label['identity'] != family_identity(m, p):
                raise ValueError('Label identity mismatch')
        complete.append((row, entries))
    return complete, skipped


def write_index(output, report):
    esc = html.escape
    lines = ['<!doctype html><html lang="en"><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             '<title>Shinka · labeled arrangements</title><style>body{background:#0b1122;color:#ecf2ff;'
             'font:17px system-ui;max-width:1100px;margin:3rem auto;padding:0 1rem}a{color:#81c9ff}'
             'article{border-top:1px solid #39445f;padding:1rem 0}audio{width:100%}'
             '.mixes{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1rem}'
             'summary{cursor:pointer;padding:1rem 0}small{color:#b3c0da}h1{color:#86ccff}</style>',
             '<h1>Your labeled arrangements</h1><p>Original melodies, new instruments guided by your notebook. '
             'First-pass offline auditions, not native game playback. Full WAV mixes and aligned lossless stems are local files.</p>',
             '<p>Sampled uses CC0 recordings plus named synthetic substitutes. DS adds sample-rate color and a light room; '
             'Chip uses procedural voices. Percussion is reduced by 4 dB and bass by 2.5 dB relative to the source stems. '
             'Tentative labels, substitute instruments and unsupported controls are recorded in each arrangement.json.</p>']
    if (output/'Shinka-labeled-listening-samples.zip').exists():
        lines.append('<p><a download href="Shinka-labeled-listening-samples.zip">Download all listening copies (ZIP)</a></p>')
    lines.append('<nav aria-label="Tracks">'+' · '.join(
        f'<a href="#{esc(t["id"])}">{esc(t["title"])}</a>' for t in report['tracks'])+'</nav>')
    for record in report['tracks']:
        tid = record['id']
        lines.append(f'<article id="{esc(tid)}"><h2>{esc(record["title"])} <small>{tid}</small></h2>')
        lines.append(f'<p>{esc(record["scene"])}</p><div class="mixes">')
        for palette in ('sampled', 'ds', 'chip'):
            src = f'{tid}/{palette}.wav'
            preview = f'{tid}/{palette}.mp3' if (output/tid/(palette+'.mp3')).exists() else src
            title = 'DS' if palette=='ds' else palette.title()
            lines.append(f'<div><b>{title}</b><audio aria-label="{esc(record["title"])} — {title}" controls preload="none" src="{preview}"></audio>'
                         f'<a download href="{src}">Download WAV</a> · '
                         f'<a download href="{preview}">Listening copy</a></div>')
        lines.append('</div><details><summary>Instrument choices & individual parts</summary>')
        for part in record['parts']:
            lines.append(f'<p><b>Part {part["part"]}: {esc(part["label"]["instrument"])}</b> '
                         f'({esc(part["label"]["confidence"])}) → {esc(part["voice"])}<br>'
                         f'{esc(part["label"].get("notes", ""))}<br>')
            for palette in ('sampled', 'ds', 'chip'):
                filename = f'{palette}-part-{part["part"]:02}'
                extension = '.flac' if (output/tid/(filename+'.flac')).exists() else '.wav'
                href = f'{tid}/{filename}{extension}'
                lines.append(f'<a href="{href}">{palette.title()} stem</a> · ')
            lines.append('</p>')
        lines.append(f'</details><a href="{tid}/arrangement.json">Full arrangement record</a></article>')
    lines.append('<h2>Preserved sound-effect cues</h2><p>These short sequences were labeled as sound effects, not songs.</p>')
    for cue in report['cues']:
        lines.append(f'<p><a href="{cue["file"]}">{cue["id"]}</a> — unchanged original-sample offline audition</p>')
    lines.append('<script>document.addEventListener("play",e=>{if(e.target.tagName==="AUDIO")'
                 'document.querySelectorAll("audio").forEach(a=>{if(a!==e.target)a.pause()})},true)</script></html>')
    (output/'index.html').write_text('\n'.join(lines), encoding='utf-8')
    (output/'arrangements.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, default=Path('output/music-ost-split-03'))
    parser.add_argument('--exports', type=Path, default=Path('output/music-catalog-export'))
    parser.add_argument('--labels', type=Path, default=Path('output/music-instrument-labels.json'))
    parser.add_argument('--instruments', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--track', action='append')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new output directory; existing auditions are never overwritten')
    labels_bytes = args.labels.read_bytes()
    labels = json.loads(labels_bytes)['labels']
    batch = json.loads((args.library/'batch.json').read_text())
    complete, skipped = completed_tracks(batch, labels)
    args.output.mkdir(parents=True)
    (args.output/'labels-snapshot.json').write_bytes(labels_bytes)
    library = Library(args.instruments)
    report = dict(tracks=[], cues=[], skipped=skipped, labels_sha256=hashlib.sha256(labels_bytes).hexdigest())
    for row, entries in complete:
        if args.track and row['id'] not in args.track:
            continue
        m, tid = row['manifest'], row['id']
        if all(route(x)=='original' for x in entries):
            source = args.library/tid/m['parts'][0]['file']
            name = tid+'-original-cue.wav'
            (args.output/name).write_bytes(source.read_bytes())
            report['cues'].append(dict(id=tid, file=name))
            continue
        export = args.exports/m['bank']
        metadata = json.loads((export/'music.json').read_text())
        data = (export/f'sequence-{m["sequence"]:03}.mid').read_bytes()
        if metadata['inputs']!=m['source_sha256'] or hashlib.sha256(data).hexdigest()!=m['midi_sha256']:
            raise ValueError(f'Source identity mismatch: {tid}')
        timeline, frames = read_score(data)
        folder = args.output/tid
        folder.mkdir()
        context = m.get('context') or {}
        rec = dict(id=tid, title=context.get('title', tid), scene=context.get('scene', 'Scene unverified'),
                   source_sha256=m['source_sha256'], midi_sha256=m['midi_sha256'], parts=[], mixes={})
        mixes = {p: np.zeros((frames+2*RATE, 2), dtype=np.float32) for p in ('sampled', 'ds', 'chip')}
        for part, label in zip(m['parts'], entries):
            voice = route(label)
            events = split_events(timeline, part['programs'])
            with wave.open(str(args.library/tid/part['file'])) as f:
                original = np.frombuffer(f.readframes(f.getnframes()), dtype='<i2').astype(np.float32).reshape(-1, 2)/32768
            target = rms(original)
            factor = 10**(-4/20) if voice=='kit' or voice.startswith('drum-') or voice in ('bongo','cajon','triangle','timpani') else 10**(-2.5/20) if voice=='bass' else 1
            pr = dict(part=part['part'], programs=part['programs'], label=label, voice=voice,
                      target_rms=target*factor, palettes={})
            for palette in mixes:
                if voice=='original':
                    audio, sources, ignored = original.copy(), ['Preserved original source'], part['ignored_events']
                else:
                    audio, sources, ignored = render_part(events, frames, metadata['bank'], part['programs'], label, palette, library)
                    level = rms(audio)
                    if level<1e-8:
                        raise ValueError(f'Silent part {tid}/{part["part"]}/{palette}')
                    audio *= target*factor/level
                    if palette=='ds':
                        audio = room_mix(audio, dict(sample_rate=RATE, cutoff_hz=12000, room_mix=.09))
                mixes[palette] += audio
                np.save(folder/f'{palette}-part-{part["part"]:02}.npy', audio)
                pr['palettes'][palette] = dict(sources=sources, ignored=ignored)
            rec['parts'].append(pr)
            print(tid, 'part', part['part'], label['instrument'], '->', voice, flush=True)
        # One common gain across all palettes and stems: summing stems reproduces
        # its mix and palette comparisons do not get separate loudness boosts.
        peak = max(float(np.max(np.abs(a))) for a in mixes.values())
        gain = min(.89/max(peak, 1e-8), .12/max(rms(a) for a in mixes.values()))
        for palette, mix in mixes.items():
            for part in m['parts']:
                spool = folder/f'{palette}-part-{part["part"]:02}.npy'
                audio = np.load(spool)*gain
                audio[-1102:] *= np.linspace(1, 0, 1102)[:, None]
                write_audio(spool.with_suffix('.wav'), audio)
                spool.unlink()
            mix *= gain
            mix[-1102:] *= np.linspace(1, 0, 1102)[:, None]
            write_audio(folder/f'{palette}.wav', mix)
            rec['mixes'][palette] = dict(peak=float(np.max(np.abs(mix))), rms=rms(mix), seconds=len(mix)/RATE)
        rec['common_gain'] = gain
        (folder/'arrangement.json').write_text(json.dumps(rec, indent=2)+'\n', encoding='utf-8')
        report['tracks'].append(rec)
        write_index(args.output, report)
        print('FINISHED', tid, flush=True)
    write_index(args.output, report)


if __name__ == '__main__':
    main()
