"""Render one guarded arrangement as sampled, chip, or DS-inspired hybrid audio.

Offline auditions only. Does not alter the runtime or implement PS1 SPU fidelity.
Requires numpy; sampled and DS backends additionally require tinysoundfont 0.3.7.
"""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct
import wave

import numpy as np
from music_export import midi_events, require
from music_chip import ChipSynth
from music_ds import HybridSynth, split_channels, validate_mix
from music_fetch_banks import CATALOG, checked
from music_context import track_context, listening_notes

PROFILE = Path(__file__).resolve().parents[1] / 'assets/music/bgm001-audition.json'
DS_PROFILE = PROFILE.with_name('bgm001-ds.json')
CONTROLLERS = {7, 10, 11, 64, 120, 121, 123}
WAVES = {'triangle', 'pulse', 'square', 'wave', 'drums'}


def mapped_key(route, key):
    if 'key_map' in route:
        require(str(key) in route['key_map'], f'Unmapped percussion key {key}')
        key = route['key_map'][str(key)]
    require(isinstance(key, int) and 0 <= key <= 127, 'Invalid mapped key')
    return key


def soundfont_key(route, key):
    if 'soundfont_key_map' in route:
        require(str(key) in route['soundfont_key_map'], f'Unmapped SoundFont key {key}')
        key = route['soundfont_key_map'][str(key)]
    key += route.get('soundfont_key_offset', 0)
    require(isinstance(key, int) and 0 <= key <= 127, 'Invalid SoundFont key')
    return key


def score(data, profile, rate):
    require(hashlib.sha256(data).hexdigest() == profile['midi_sha256'],
            'MIDI does not match this arrangement profile; author a separate mapping')
    require(data[:4] == b'MThd' and len(data) >= 22, 'Missing MIDI header')
    size, fmt, tracks, ppqn = struct.unpack_from('>I3H', data, 4)
    require(size == 6 and fmt == 0 and tracks == 1 and 0 < ppqn < 32768, 'Expected format-0 PPQN MIDI')
    require(data[14:18] == b'MTrk' and struct.unpack_from('>I', data, 18)[0] == len(data) - 22,
            'MIDI track extent mismatch')
    events = midi_events(data[22:])
    programs = [0] * 16
    assigned = {}
    timeline = []
    ignored = Counter()
    seconds = Fraction(0)
    tick = 0
    tempo = 500000
    note_count = 0
    for event in events:
        seconds += Fraction((event['tick'] - tick) * tempo, ppqn * 1000000)
        tick = event['tick']
        status, payload = event['status'], event['data']
        channel, kind = status & 15, status & 0xf0
        if status == 255:
            if event['meta'] == 0x51:
                tempo = int.from_bytes(bytes(payload), 'big')
                require(tempo > 0, 'Zero tempo')
            continue
        if kind == 0xc0:
            programs[channel] = payload[0]
            continue
        if kind == 0x90 and payload[1]:
            program = programs[channel]
            require(str(program) in profile['programs'], f'Unmapped program {program}')
            require(channel not in assigned or assigned[channel] == program,
                    'Audition renderer requires one instrument per source channel')
            assigned[channel] = program
            route = profile['programs'][str(program)]
            soundfont_key(route, mapped_key(route, payload[0]))
            note_count += 1
        if kind == 0xb0 and payload[0] not in CONTROLLERS:
            ignored[f'CC{payload[0]}'] += 1
            continue
        if kind not in (0x80, 0x90, 0xb0, 0xe0):
            ignored[f'status-{status:02x}'] += 1
            continue
        timeline.append((round(seconds * rate), status, payload))
    require(0 < seconds <= 600 and note_count > 0, 'Expected a nonempty song of at most ten minutes')
    channels = {ch: profile['programs'][str(program)] for ch, program in assigned.items()}
    for route in channels.values():
        require(route['chip'] in WAVES, 'Unknown chip waveform')
        require(0 < route['gain'] <= 1 and 0 <= route['pan'] <= 1, 'Invalid route gain/pan')
        require(-24 <= route.get('soundfont_tuning', 0) <= 24, 'Invalid SoundFont tuning')
        adsr = route.get('adsr', [.004, .14, .55, .12])
        require(len(adsr) == 4 and all(np.isfinite(x) for x in adsr) and
                0 < adsr[0] <= 2 and 0 < adsr[1] <= 4 and 0 <= adsr[2] <= 1 and
                0 < adsr[3] <= 2, 'Invalid audition ADSR')
    return timeline, channels, dict(seconds_one_pass=float(seconds), frames=round(seconds * rate),
                                    notes=note_count, ignored_events=dict(ignored),
                                    channels={str(ch): p for ch, p in assigned.items()})


class SoundFontSynth:
    def __init__(self, channels, banks, rate):
        from importlib.metadata import version
        require(version('tinysoundfont') == '0.3.7', 'Install the pinned tinysoundfont 0.3.7 renderer')
        from tinysoundfont import Synth
        self.synth = Synth(gain=-12, samplerate=rate)
        self.channels = channels
        self.volumes = {ch: 127 for ch in channels}
        catalog = json.loads(CATALOG.read_text(encoding='utf-8'))['banks']
        loaded = {}
        for name in sorted({r['soundfont'] for r in channels.values()}):
            require(name in catalog, f'Unknown CC0 bank {name}')
            data = checked((banks / f'{name}.sf2').read_bytes(), catalog[name]['sha256'])
            loaded[name] = self.synth.sfload(data)
        for ch, route in channels.items():
            sfid = loaded[route['soundfont']]
            require(self.synth.sfpreset_name(sfid, 0, 0) is not None, 'Missing expected preset')
            # Every selected bank uses bank 0, preset 0, even the drum bank.
            # Source channel 9 remains melodic if its route says so.
            self.synth.program_select(ch, sfid, 0, 0, is_drums=False)
            self.synth.pitchbend_range(ch, 2)
            self.synth.set_tuning(ch, route.get('soundfont_tuning', 0))
            self.control_change(ch, 7, 127)
            self.synth.control_change(ch, 10, round(route['pan'] * 127))

    def noteon(self, channel, key, velocity):
        self.synth.noteon(channel, soundfont_key(self.channels[channel], key), velocity)

    def noteoff(self, channel, key):
        self.synth.noteoff(channel, soundfont_key(self.channels[channel], key))

    def control_change(self, channel, controller, value):
        if controller == 7:
            self.volumes[channel] = value
            value = round(value * self.channels[channel]['gain'])
        self.synth.control_change(channel, controller, value)
        if controller == 121:
            self.control_change(channel, 7, self.volumes[channel])
            self.synth.set_tuning(channel, self.channels[channel].get('soundfont_tuning', 0))

    def pitchbend(self, channel, value):
        self.synth.pitchbend(channel, value)

    def finish(self):
        for ch in self.channels:
            self.synth.control_change(ch, 64, 0)
            self.synth.notes_off(ch)

    def render(self, frames):
        return np.frombuffer(self.synth.generate_simple(frames), dtype=np.float32).reshape(-1, 2).copy()


def verify_soundfont_keys(timeline, channels, banks, rate):
    """Isolated preflight: each used channel/key must produce non-silent audio."""
    probe = SoundFontSynth(channels, banks, rate)
    keys = sorted({(status & 15, mapped_key(channels[status & 15], payload[0]))
                   for _, status, payload in timeline
                   if status & 0xf0 == 0x90 and payload[1] and status & 15 in channels})
    for channel, key in keys:
        probe.synth.sounds_off()
        probe.render(round(.1 * rate))
        probe.noteon(channel, key, 100)
        audio = probe.render(round(.25 * rate))
        require(np.max(np.abs(audio)) > 1e-7, f'Silent SoundFont route: channel {channel}, key {key}')
    return len(keys)


def render(timeline, channels, info, synth, rate, tail=2):
    audio = np.zeros((info['frames'] + round(tail * rate), 2), dtype=np.float32)
    position = 0

    def advance(end):
        nonlocal position
        while position < end:
            count = min(2048, end - position)
            audio[position:position + count] = synth.render(count)
            position += count

    for frame, status, payload in timeline:
        advance(frame)
        ch, kind = status & 15, status & 0xf0
        if ch not in channels:
            continue
        if kind in (0x80, 0x90):
            key = mapped_key(channels[ch], payload[0])
            if kind == 0x90 and payload[1]:
                synth.noteon(ch, key, payload[1])
            else:
                synth.noteoff(ch, key)
        elif kind == 0xb0:
            synth.control_change(ch, payload[0], payload[1])
        elif kind == 0xe0:
            synth.pitchbend(ch, payload[0] | payload[1] << 7)
    advance(info['frames'])
    synth.finish()
    advance(len(audio))
    if hasattr(synth, 'process_audio'):
        audio = synth.process_audio(audio)
    require(np.all(np.isfinite(audio)), 'Non-finite synth output')
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
    require(peak > 1e-7 and rms > 1e-8, 'Synth produced silence')
    # Comparable RMS targets, limited by peak headroom; no clipping limiter.
    gain = min(.1 / rms, .89 / peak)
    audio *= gain
    # End gracefully even if a SoundFont has a release longer than the tail.
    fade = min(round(rate * .025), len(audio))
    audio[-fade:] *= np.linspace(1, 0, fade)[:, None]
    metrics = dict(raw_peak=peak, raw_rms=rms, normalization_gain=gain,
                   final_peak=float(np.max(np.abs(audio))),
                   final_rms=float(np.sqrt(np.mean(audio.astype(np.float64) ** 2))),
                   sample_rate=rate, frames=len(audio), tail_seconds=tail,
                   stolen_voices=getattr(synth, 'stolen', None),
                   peak_voices=getattr(synth, 'peak_voices', None))
    return audio, metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('midi', type=Path)
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--backend', choices=('chip', 'soundfont', 'ds'), default='ds',
                        help='Audition palette (default: ds)')
    parser.add_argument('--banks', type=Path, default=Path('output/music-banks'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        require(not args.output.exists(), 'Choose a new output directory')
        profile_path = args.profile or (DS_PROFILE if args.backend == 'ds' else PROFILE)
        profile_bytes = profile_path.read_bytes()
        profile = json.loads(profile_bytes)
        rate = validate_mix(profile['ds_mix']) if args.backend == 'ds' else 44100
        timeline, channels, info = score(args.midi.read_bytes(), profile, rate)
        if args.backend == 'ds':
            sampled, chip = split_channels(channels)
            info['verified_soundfont_keys'] = verify_soundfont_keys(timeline, sampled, args.banks, rate)
            synth = HybridSynth(SoundFontSynth(sampled, args.banks, rate),
                                ChipSynth(chip, rate), channels, profile['ds_mix'])
        elif args.backend == 'soundfont':
            info['verified_soundfont_keys'] = verify_soundfont_keys(timeline, channels, args.banks, rate)
            synth = SoundFontSynth(channels, args.banks, rate)
        else:
            synth = ChipSynth(channels, rate)
        audio, metrics = render(timeline, channels, info, synth, rate)
        args.output.mkdir(parents=True)
        with wave.open(str(args.output / 'preview.wav'), 'wb') as file:
            file.setparams((2, 2, rate, 0, 'NONE', 'not compressed'))
            file.writeframes(np.rint(audio * 32767).astype('<i2').tobytes())
        report = dict(backend=args.backend, arrangement=profile['name'],
                      profile_sha256=hashlib.sha256(profile_bytes).hexdigest(),
                      midi_sha256=profile['midi_sha256'], score=info, audio=metrics,
                      limitations=['Offline creative audition; not original SPU emulation.',
                                   'Custom PS1 controllers and sequence loops are not interpreted.',
                                   'Instrument identities and balancing are provisional.'])
        report['track_context'] = track_context(report['midi_sha256'])
        (args.output / 'listening-notes.md').write_text(
            listening_notes(report['track_context'], args.backend), encoding='utf-8')
        if args.backend in ('soundfont', 'ds'):
            report['banks'] = json.loads(CATALOG.read_text(encoding='utf-8'))
            report['renderer'] = 'tinysoundfont 0.3.7 (MIT), offline float output'
        if args.backend == 'ds':
            report['mix'] = profile['ds_mix']
            report['routes'] = {str(ch): route['renderer'] for ch, route in channels.items()}
            report['chip_bus'] = dict(peak_voices=synth.chip.peak_voices, stolen_voices=synth.chip.stolen)
            report['limitations'].append('DS-inspired palette; no DS hardware timing or global 16-voice limit.')
        (args.output / 'preview.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(dict(output=str(args.output), **metrics)))
    except (OSError, ValueError, KeyError, ImportError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
