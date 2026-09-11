import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from music_export import encode_events, wav_bytes
from split_music_ost import OriginalSynth, batch, read_score, render, split_events


def event(tick, status, *data, **kw):
    return dict(tick=tick, status=status, data=list(data), **kw)


def midi(events):
    body = encode_events(events)
    return b'MThd'+struct.pack('>I3H', 6, 0, 1, 96)+b'MTrk'+struct.pack('>I', len(body))+body


def bank():
    tone = dict(sample=1, volume=127, pan=64, root_key=60, fine_tuning=0,
                key_min=0, key_max=127, pitch_bend_up=2, pitch_bend_down=2,
                adsr1=15, adsr2=0x1fc0)
    return dict(master_volume=127, master_pan=64,
                programs=[dict(program=0, volume=127, pan=64, tones=[tone])],
                samples=[dict(id=1, wav='sample-001.wav', frames=100, loop_frames=[0, 100])])


class OstSplitTests(unittest.TestCase):
    def test_tempo_changes_and_program_change_noteoff_ownership(self):
        data = midi([event(0, 0xc0, 0), event(0, 0x90, 60, 100),
                     event(96, 255, 15, 66, 64, meta=0x51),  # 1 second per quarter
                     event(96, 0xc0, 1), event(96, 0x90, 60, 100),
                     event(192, 0x80, 60, 0), event(288, 0x80, 60, 0),
                     event(288, 255, meta=0x2f)])
        timeline, frames = read_score(data)
        self.assertEqual(frames, 110250)
        a, b = split_events(timeline, {0}), split_events(timeline, {1})
        self.assertEqual([f for f, e in a if e['status'] == 0x80], [66150])
        self.assertEqual([f for f, e in b if e['status'] == 0x80], [110250])
        self.assertEqual(a[-1], b[-1])  # common track extent preserved

    def test_sample_pitch_loop_sustain_and_release(self):
        original = 10000*np.sin(np.arange(100)*2*np.pi/100)
        synth = OriginalSynth(bank(), {1: (original, [0, 100])})
        synth.event(event(0, 0x90, 72, 127))
        pcm = synth.render(44100)
        self.assertEqual(np.argmax(np.abs(np.fft.rfft(pcm[22050:, 0])))*2, 882)
        synth.event(event(0, 0xb0, 64, 127))
        synth.event(event(0, 0x80, 72, 0))
        self.assertIsNone(synth.voices[0]['released'])
        synth.event(event(0, 0xb0, 64, 0))
        self.assertIsNotNone(synth.voices[0]['released'])
        synth.render(44100)
        self.assertEqual(synth.voices, [])

    def test_layered_tones_release_together_and_custom_controls_reported(self):
        b = bank()
        b['programs'][0]['tones'] *= 2
        samples = {1: (np.ones(100)*10000, [0, 100])}
        synth = OriginalSynth(b, samples)
        synth.event(event(0, 0x90, 60, 100))
        self.assertEqual(len(synth.voices), 2)
        synth.render(100)
        synth.event(event(0, 0x80, 60, 0))
        self.assertTrue(all(v['released'] is not None for v in synth.voices))
        timeline, frames = read_score(midi([event(0, 0xb0, 99, 20), event(0, 0x90, 60, 100),
                                            event(192, 0x80, 60, 0), event(192, 255, meta=0x2f)]))
        audio, ignored = render(timeline, frames, b, samples)
        self.assertEqual(ignored, {'CC99': 1})
        self.assertEqual(audio.shape, (132300, 2))
        self.assertFalse(np.any(audio[-44100:]))

    def test_unmapped_keys_are_reported_without_substituting_an_instrument(self):
        b = bank()
        b['programs'][0]['tones'][0].update(key_min=60, key_max=60)
        synth = OriginalSynth(b, {1: (np.ones(100), [0, 100])})
        synth.event(event(0, 0x90, 48, 100))
        self.assertEqual(synth.voices, [])
        self.assertEqual(synth.unsupported, {'unmapped-key-program-0-key-48': 1})

    def test_fractional_loop_boundary_has_no_zero_gap(self):
        synth = OriginalSynth(bank(), {1: (np.ones(100)*10000, [0, 100])})
        synth.event(event(0, 0x90, 67, 127))
        synth.render(1000)  # settle attack
        audio = synth.render(1000)
        np.testing.assert_allclose(audio[:, 0], audio[0, 0], atol=.001)

    def test_batch_uses_all_declared_sequences_not_assumed_sequence_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export = root/'exports'/'BGM031'
            export.mkdir(parents=True)
            b = bank()
            (export/'sample-001.wav').write_bytes(wav_bytes([10000]*100, [0, 100]))
            (export/'sequence-002.mid').write_bytes(midi([event(0, 0x90, 60, 100),
                                                         event(192, 0x80, 60, 0),
                                                         event(192, 255, meta=0x2f)]))
            meta = dict(inputs={'owned': 'example'}, bank=b, sequences=[
                dict(id=0, seconds_one_pass=.001, unmapped_programs=[127], program_usage=[]),
                dict(id=2, seconds_one_pass=1, unmapped_programs=[],
                     program_usage=[dict(program=0, notes=1)])])
            (export/'music.json').write_text(json.dumps(meta))
            result = batch(root/'exports', root/'out')
            self.assertEqual(len(result['tracks']), 1)
            self.assertEqual(len(result['skipped']), 1)
            self.assertEqual(result['errors'], [])
            track = result['tracks'][0]
            self.assertEqual(track['id'], 'BGM031-002')
            self.assertEqual(track['manifest']['renderer'], 'offline-original-sample-approximation-v1')
            with wave.open(str(root/'out'/'BGM031-002'/'part-01.wav')) as f:
                self.assertEqual(f.getnframes(), 132300)
                pcm = np.frombuffer(f.readframes(f.getnframes()), dtype='<i2')
                self.assertGreater(np.max(np.abs(pcm)), 0)
                self.assertLessEqual(np.max(np.abs(pcm)), 30000)
            self.assertTrue((root/'out'/'index.html').exists())
            with self.assertRaisesRegex(ValueError, 'new output'):
                batch(root/'exports', root/'out')
            (export/'sample-001.wav').write_bytes(b'broken')
            # Invalid source data must be reported, never replaced by a silent success.
            result = batch(root/'exports', root/'failed')
            self.assertEqual(len(result['errors']), 1)
            self.assertEqual(result['tracks'], [])


if __name__ == '__main__':
    unittest.main()
