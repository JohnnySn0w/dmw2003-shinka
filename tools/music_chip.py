"""Deterministic oscillator audition synth; inspired by chips, not PS1 emulation."""
import math
import numpy as np


def envelope(age, attack, decay, sustain):
    return np.where(age < attack, age / attack,
                    sustain + (1 - sustain) * np.maximum(0, 1 - (age - attack) / decay))


def blep(phase, step):
    start = np.clip(phase / step, 0, 1)
    end = np.clip((phase - 1) / step, -1, 0)
    return np.where(phase < step, 2 * start - start * start - 1, 0) + np.where(
        phase > 1 - step, end * end + 2 * end + 1, 0)


class ChipSynth:
    def __init__(self, channels, rate=44100, max_voices=24):
        if not 8000 <= rate <= 96000 or not 1 <= max_voices <= 128:
            raise ValueError('Invalid synth rate or voice limit')
        self.rate = rate
        self.channels = channels
        self.max_voices = max_voices
        self.voices = []
        self.serial = self.stolen = self.peak_voices = 0
        self.controls = {ch: dict(volume=1., expression=1., pan=r['pan'], bend=0., sustain=False)
                         for ch, r in channels.items()}

    def noteon(self, channel, key, velocity):
        if not velocity:
            self.noteoff(channel, key)
            return
        if len(self.voices) >= self.max_voices:
            # Prefer a releasing voice, then the oldest held voice.
            victim = min(self.voices, key=lambda v: (v['released'] is None, v['serial']))
            self.voices.remove(victim)
            self.stolen += 1
        route = self.channels[channel]
        wave = route['chip']
        attack, decay, sustain, release = route.get('adsr', [.004, .14, .55, .12])
        if wave == 'drums':
            wave = 'kick' if key in (35, 36) else 'tom' if key in (41, 43, 45, 47, 48, 50) else 'noise'
            decay = .3 if key in (46, 49, 52) else .11
            attack, sustain, release = .001, 0., .04
        self.serial += 1
        self.voices.append(dict(channel=channel, key=key, velocity=velocity / 127,
                                serial=self.serial, phase=0., age=0, released=None,
                                release_level=0., held=True, rng=np.random.default_rng(self.serial),
                                wave=wave, adsr=(attack, decay, sustain, release), gain=route['gain']))
        self.peak_voices = max(self.peak_voices, len(self.voices))

    def release(self, voice):
        if voice['released'] is None:
            a, d, s, _ = voice['adsr']
            voice['released'] = voice['age']
            voice['release_level'] = float(envelope(voice['age'] / self.rate, a, d, s))

    def noteoff(self, channel, key):
        for v in self.voices:
            if v['channel'] == channel and v['key'] == key and v['held']:
                v['held'] = False
                if not self.controls[channel]['sustain']:
                    self.release(v)
                break

    def control_change(self, channel, controller, value):
        c = self.controls[channel]
        if controller in (7, 11):
            c['volume' if controller == 7 else 'expression'] = value / 127
        elif controller == 10:
            c['pan'] = value / 127
        elif controller == 64:
            c['sustain'] = value >= 64
            if not c['sustain']:
                for v in self.voices:
                    if v['channel'] == channel and not v['held']:
                        self.release(v)
        elif controller == 120:
            self.voices = [v for v in self.voices if v['channel'] != channel]
        elif controller == 123:
            for v in self.voices:
                if v['channel'] == channel:
                    v['held'] = False
                    if not c['sustain']:
                        self.release(v)
        elif controller == 121:
            c.update(expression=1., bend=0., sustain=False)
            for v in self.voices:
                if v['channel'] == channel and not v['held']:
                    self.release(v)

    def pitchbend(self, channel, value):
        self.controls[channel]['bend'] = (value - 8192) / 8192 * 2

    def finish(self):
        for channel in self.channels:
            self.control_change(channel, 64, 0)
            self.control_change(channel, 123, 0)

    def render(self, frames):
        out = np.zeros((frames, 2), dtype=np.float32)
        offsets = np.arange(frames)
        keep = []
        for v in self.voices:
            c = self.controls[v['channel']]
            age = (v['age'] + offsets) / self.rate
            a, d, s, r = v['adsr']
            amp = envelope(age, a, d, s)
            if v['released'] is not None:
                amp = v['release_level'] * np.maximum(0, 1 - (age - v['released'] / self.rate) / r)
            freq = min(self.rate * .45, 440 * 2 ** ((v['key'] + c['bend'] - 69) / 12))
            step = freq / self.rate
            phase = (v['phase'] + offsets * step) % 1
            kind = v['wave']
            if kind in ('pulse', 'square'):
                duty = .25 if kind == 'pulse' else .5
                signal = np.where(phase < duty, 1., -1.) + blep(phase, step) - blep((phase - duty) % 1, step)
                signal -= 2 * duty - 1
            elif kind == 'triangle':
                signal = 1 - 4 * np.abs(phase - .5)
            elif kind == 'wave':
                # A short, quantized waveform table gives the lead a chip-like edge.
                table_phase = np.floor(phase * 32) / 32 * 2 * np.pi
                signal = (np.sin(table_phase) + .28 * np.sin(3 * table_phase)) / 1.28
                signal = np.round(signal * 31) / 31
            elif kind == 'noise':
                signal = v['rng'].choice((-1., 1.), size=frames)
            elif kind in ('kick', 'tom'):
                base = 45 if kind == 'kick' else freq * 2
                signal = np.sin(2 * np.pi * (base * age + 100 * .025 * (1 - np.exp(-age / .025))))
            else:
                raise ValueError(f'Unknown chip waveform: {kind}')
            signal *= amp * v['velocity'] * v['gain'] * c['volume'] * c['expression'] * .14
            pan = c['pan'] * math.pi / 2
            out[:, 0] += signal * math.cos(pan)
            out[:, 1] += signal * math.sin(pan)
            v['phase'] = (v['phase'] + frames * step) % 1
            v['age'] += frames
            if v['released'] is not None:
                alive = (v['age'] - v['released']) / self.rate < r
            else:
                alive = s > 0 or v['age'] / self.rate < a + d
            if alive:
                keep.append(v)
        self.voices = keep
        return out
