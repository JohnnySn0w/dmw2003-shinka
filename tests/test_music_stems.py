import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from capture_music_stems import assemble, audition_window, families


class MusicStemTests(unittest.TestCase):
    def test_key_zones_and_delayed_programs_form_sound_families(self):
        def program(p, *samples):
            return dict(program=p, tones=[dict(sample=s) for s in samples])
        meta = dict(bank=dict(programs=[program(0, 1, 2), program(1, 3),
                                       program(2, 2), program(3, 3), program(4, 5)]))
        groups = families(meta, {1, 2, 3})
        self.assertEqual(groups, [dict(programs={0, 2}, samples={1, 2}),
                                  dict(programs={1, 3}, samples={3})])

    def test_stems_remain_aligned_and_share_headroom(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output/'raw').mkdir()
            for offset, values in [(16, [[20000, -20000], [0, 0]]),
                                   (32, [[20000, -20000], [10000, -10000]]),
                                   (48, [[0, 0], [8000, -8000]])]:
                np.asarray(values, dtype='<i4').tofile(output/'raw'/f'sample-{offset}.s32le')
            meta = dict(bank=dict(samples=[dict(id=i, body_offset=i*16) for i in (1, 2, 3)],
                                  programs=[dict(program=0, tones=[dict(sample=1), dict(sample=2)]),
                                            dict(program=1, tones=[dict(sample=3)])]))
            bank = dict(samples=[dict(sample=i) for i in (1, 2, 3)])
            parts = assemble(output, meta, bank, 2)
            self.assertEqual(len(parts), 2)
            self.assertTrue(all(p['full_stem_gain'] == .75 for p in parts))
            with wave.open(str(output/'part-01.wav')) as f:
                self.assertEqual(f.getnchannels(), 2)
                pcm = np.frombuffer(f.readframes(2), dtype='<i2').reshape(-1, 2)
            np.testing.assert_array_equal(pcm, [[30000, -30000], [7500, -7500]])
            with wave.open(str(output/'part-02.wav')) as f:
                pcm = np.frombuffer(f.readframes(2), dtype='<i2').reshape(-1, 2)
            np.testing.assert_array_equal(pcm, [[0, 0], [6000, -6000]])
            json.dumps(parts)  # manifest remains serializable

    def test_audition_selects_active_passage_without_moving_full_stem(self):
        pcm = np.zeros((44100*12, 2), dtype=np.int64)
        pcm[44100*10:] = 100
        start, excerpt = audition_window(pcm, 2)
        self.assertEqual(start, 441000)
        self.assertEqual(excerpt.shape, (88200, 2))
        self.assertTrue(np.all(excerpt == 100))


if __name__ == '__main__':
    unittest.main()
