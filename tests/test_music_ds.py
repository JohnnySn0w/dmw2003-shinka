import sys
from pathlib import Path
import unittest
from unittest.mock import Mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from music_ds import HybridSynth, room_mix, split_channels, validate_mix

MIX = dict(sample_rate=32768, cutoff_hz=8000, room_mix=.12)


class MusicDSTests(unittest.TestCase):
    def test_routing_controls_and_mix_use_each_channel_once(self):
        sampled, chip = Mock(), Mock()
        channels = {9: {'renderer': 'sampled'}, 4: {'renderer': 'chip'}}
        synth = HybridSynth(sampled, chip, channels, MIX)
        synth.noteon(9, 60, 100)
        synth.noteoff(4, 62)
        synth.control_change(9, 64, 127)
        synth.pitchbend(4, 9000)
        sampled.noteon.assert_called_once_with(9, 60, 100)
        chip.noteon.assert_not_called()
        chip.noteoff.assert_called_once_with(4, 62)
        sampled.control_change.assert_called_once_with(9, 64, 127)
        chip.pitchbend.assert_called_once_with(4, 9000)
        sampled.render.return_value = np.full((100, 2), .2)
        chip.render.return_value = np.full((100, 2), .1)
        np.testing.assert_allclose(synth.render(100), .3)
        synth.finish()
        sampled.finish.assert_called_once()
        chip.finish.assert_called_once()

    def test_room_is_causal_and_reflections_cross_stereo_without_wrapping(self):
        audio = np.zeros((16000, 2), dtype=np.float32)
        audio[100, 0] = 1
        result = room_mix(audio, MIX)
        self.assertEqual(result.shape, audio.shape)
        self.assertTrue(np.all(np.isfinite(result)))
        self.assertFalse(np.any(result[:100]))
        self.assertEqual(np.argmax(result[:, 0]), 120)
        delay = round(.029 * 32768)
        self.assertFalse(np.any(result[:100 + delay, 1]))
        self.assertGreater(result[120 + delay, 1], 0)
        self.assertFalse(np.any(result[5000:]))
        np.testing.assert_array_equal(audio[100], [1, 0])

    def test_mix_reduces_high_frequency_content(self):
        time = np.arange(32768) / 32768
        audio = np.column_stack((np.sin(2 * np.pi * 1000 * time),
                                 np.sin(2 * np.pi * 12000 * time)))
        result = room_mix(audio, dict(MIX, room_mix=0))[100:]
        rms = np.sqrt(np.mean(result ** 2, axis=0))
        self.assertGreater(rms[0], .65)
        self.assertLess(rms[1], rms[0] * .03)

    def test_invalid_routes_and_mix_are_rejected(self):
        for channels in ({0: {'renderer': 'typo'}}, {0: {'renderer': 'chip'}}, {}):
            with self.assertRaises(ValueError): split_channels(channels)
        for change in (dict(sample_rate=0), dict(cutoff_hz=20000), dict(room_mix=float('nan'))):
            with self.assertRaises(ValueError): validate_mix(dict(MIX, **change))


if __name__ == '__main__': unittest.main()
