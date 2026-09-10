import copy
import hashlib
import struct
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from music_chip import ChipSynth
from music_export import sequences
from music_fetch_banks import checked
from music_preview import mapped_key, render, score, soundfont_key, verify_soundfont_keys


ROUTE = dict(chip='triangle', soundfont='piano', gain=.8, pan=.5, adsr=[.01, .1, .6, .1])


def fixture(body):
    sep = b'pQES\0\0' + struct.pack('>HH', 0, 96) + bytes.fromhex('07a1200402')
    midi = sequences(sep + struct.pack('>I', len(body)) + body)[0][1]
    profile = dict(midi_sha256=hashlib.sha256(midi).hexdigest(), programs={'5': copy.deepcopy(ROUTE)})
    return midi, profile


class MusicPreviewTests(unittest.TestCase):
    def test_shared_timing_keeps_channel_ten_melodic_and_reports_custom_cc(self):
        midi, profile = fixture(bytes.fromhex('00c90500b9631400993c4060893c0000ff5103d09030ff2f00'))
        timeline, channels, info = score(midi, profile, 44100)
        self.assertEqual(channels[9]['soundfont'], 'piano')
        self.assertEqual(info['notes'], 1)
        self.assertEqual(info['ignored_events'], {'CC99': 1})
        self.assertEqual(info['frames'], round(.625 * 44100))
        self.assertEqual(timeline[1][0], 22050)

    def test_guard_rejects_wrong_song_missing_mapping_and_program_changes(self):
        midi, profile = fixture(bytes.fromhex('00c00500903c4060803c0000ff2f00'))
        with self.assertRaisesRegex(ValueError, 'does not match'):
            score(midi + b'\0', profile, 44100)
        profile['programs'] = {}
        with self.assertRaisesRegex(ValueError, 'Unmapped program'):
            score(midi, profile, 44100)
        midi, profile = fixture(bytes.fromhex('00c00500903c4001c00600903e4000ff2f00'))
        profile['programs']['6'] = copy.deepcopy(ROUTE)
        with self.assertRaisesRegex(ValueError, 'one instrument'):
            score(midi, profile, 44100)

    def test_map_and_asset_hash_fail_closed(self):
        self.assertEqual(mapped_key({'key_map': {'36': 45}}, 36), 45)
        with self.assertRaises(ValueError): mapped_key({'key_map': {'36': 45}}, 37)
        with self.assertRaises(ValueError): mapped_key({'key_map': {'36': 128}}, 36)
        with self.assertRaises(ValueError): checked(b'changed', hashlib.sha256(b'original').hexdigest())
        self.assertEqual(soundfont_key({'soundfont_key_map': {'36': 48}}, 36), 48)
        self.assertEqual(soundfont_key({'soundfont_key_offset': -12}, 52), 40)
        with self.assertRaises(ValueError): soundfont_key({'soundfont_key_map': {'36': 48}}, 38)

    def test_waveform_output_does_not_depend_on_block_size(self):
        for kind in ('triangle', 'pulse', 'square', 'wave', 'drums'):
            with self.subTest(kind=kind):
                route = dict(ROUTE, chip=kind)
                a = ChipSynth({0: route}); b = ChipSynth({0: route})
                a.noteon(0, 38, 100); b.noteon(0, 38, 100)
                whole = a.render(4096)
                pieces = np.concatenate([b.render(n) for n in (117, 2011, 1968)])
                np.testing.assert_allclose(whole, pieces, atol=2e-7, rtol=0)

    def test_soundfont_preflight_rejects_a_silent_key(self):
        midi, profile = fixture(bytes.fromhex('00c00500903c4060803c0000ff2f00'))
        timeline, channels, _ = score(midi, profile, 44100)
        with patch('music_preview.SoundFontSynth') as fake:
            fake.return_value.render.side_effect = lambda frames: np.zeros((frames, 2))
            with self.assertRaisesRegex(ValueError, 'Silent SoundFont route'):
                verify_soundfont_keys(timeline, channels, Path('unused'), 44100)

    def test_sustain_release_and_all_sound_off(self):
        synth = ChipSynth({0: ROUTE})
        synth.noteon(0, 69, 100); synth.render(500)
        synth.control_change(0, 64, 127); synth.noteoff(0, 69)
        self.assertIsNone(synth.voices[0]['released'])
        synth.control_change(0, 64, 0)
        self.assertIsNotNone(synth.voices[0]['released'])
        synth.render(5000)
        self.assertEqual(synth.voices, [])
        synth.noteon(0, 69, 100); synth.control_change(0, 120, 0)
        self.assertFalse(np.any(synth.render(100)))

    def test_voice_limit_prefers_releasing_voice(self):
        synth = ChipSynth({0: ROUTE}, max_voices=2)
        synth.noteon(0, 60, 100); synth.noteon(0, 62, 100)
        synth.noteoff(0, 62); synth.noteon(0, 64, 100)
        self.assertEqual([v['key'] for v in synth.voices], [60, 64])
        synth.noteon(0, 65, 100)
        self.assertEqual([v['key'] for v in synth.voices], [64, 65])
        self.assertEqual((synth.peak_voices, synth.stolen), (2, 2))

    def test_pitch_pan_and_volume(self):
        synth = ChipSynth({0: dict(ROUTE, adsr=[.001, .001, 1, .1])})
        synth.noteon(0, 69, 127); synth.pitchbend(0, 16383)
        synth.control_change(0, 10, 0)
        audio = synth.render(44100)
        spectrum = np.abs(np.fft.rfft(audio[:, 0]))
        self.assertEqual(np.argmax(spectrum), 494)  # A4 bent up two semitones.
        self.assertFalse(np.any(audio[:, 1]))
        synth.control_change(0, 7, 0)
        self.assertFalse(np.any(synth.render(100)))

    def test_render_tail_and_headroom(self):
        midi, profile = fixture(bytes.fromhex('00c00500903c4060803c0000ff2f00'))
        timeline, channels, info = score(midi, profile, 44100)
        synth = ChipSynth(channels)
        audio, metrics = render(timeline, channels, info, synth, 44100)
        self.assertEqual(len(audio), 110250)
        self.assertLessEqual(metrics['final_peak'], .891)
        self.assertTrue(np.all(np.isfinite(audio)))
        self.assertTrue(np.any(audio[:22050]))
        self.assertFalse(np.any(audio[-44100:]))


if __name__ == '__main__': unittest.main()
