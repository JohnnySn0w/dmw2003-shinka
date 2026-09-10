"""DS-inspired sample/oscillator palette and mix; not a hardware emulator."""
import numpy as np


def split_channels(channels):
    groups = {'sampled': {}, 'chip': {}}
    for channel, route in channels.items():
        renderer = route.get('renderer')
        if renderer not in groups:
            raise ValueError(f'Choose sampled or chip renderer for channel {channel}')
        groups[renderer][channel] = route
    if not all(groups.values()):
        raise ValueError('DS hybrid requires both sampled and chip voices')
    return groups['sampled'], groups['chip']


def validate_mix(mix):
    rate, cutoff, wet = mix['sample_rate'], mix['cutoff_hz'], mix['room_mix']
    if not isinstance(rate, int) or not 16000 <= rate <= 48000:
        raise ValueError('Invalid DS audition sample rate')
    if not np.isfinite(cutoff) or not 1000 <= cutoff < rate * .45:
        raise ValueError('Invalid DS audition bandwidth')
    if not np.isfinite(wet) or not 0 <= wet <= .4:
        raise ValueError('Invalid DS audition room level')
    return rate


def room_mix(audio, mix):
    """Finite, causal low-pass and early reflections; no wraparound or feedback."""
    rate = validate_mix(mix)
    points = np.arange(41) - 20
    cutoff = mix['cutoff_hz'] / rate
    kernel = 2 * cutoff * np.sinc(2 * cutoff * points) * np.hamming(41)
    kernel /= kernel.sum()
    dry = np.column_stack([np.convolve(audio[:, ch], kernel, mode='full')[:len(audio)]
                           for ch in range(2)]).astype(np.float32)
    out = dry.copy()
    for index, (seconds, gain) in enumerate(((.029, .4), (.043, .3), (.071, .2), (.113, .1))):
        offset = round(seconds * rate)
        if offset < len(audio):
            reflection = dry[:-offset, ::-1] if index % 2 == 0 else dry[:-offset]
            out[offset:] += reflection * gain * mix['room_mix']
    return out


class HybridSynth:
    def __init__(self, sampled, chip, channels, mix):
        validate_mix(mix)
        split_channels(channels)
        self.sampled, self.chip = sampled, chip
        self.channels, self.mix = channels, mix

    def target(self, channel):
        return self.sampled if self.channels[channel]['renderer'] == 'sampled' else self.chip

    def noteon(self, channel, key, velocity):
        self.target(channel).noteon(channel, key, velocity)

    def noteoff(self, channel, key):
        self.target(channel).noteoff(channel, key)

    def control_change(self, channel, controller, value):
        self.target(channel).control_change(channel, controller, value)

    def pitchbend(self, channel, value):
        self.target(channel).pitchbend(channel, value)

    def finish(self):
        self.sampled.finish()
        self.chip.finish()

    def render(self, frames):
        return self.sampled.render(frames) + self.chip.render(frames)

    def process_audio(self, audio):
        return room_mix(audio, self.mix)
