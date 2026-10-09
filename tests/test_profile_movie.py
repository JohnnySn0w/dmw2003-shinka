import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from profile_movie import analyze


class MovieTimingTests(unittest.TestCase):
    def frames(self):
        return [dict(f=i, input=i*20000, swap_begin=i*20000+500,
                     swap_end=i*20000+600) for i in range(100)]

    def test_measures_brief_stall_hidden_by_average(self):
        frames = self.frames()
        frames[50]['swap_end'] += 15000
        result = analyze(frames, 0, 100)
        self.assertEqual(result['delivery']['mean_ms'], 20)
        self.assertEqual(result['delivery']['max_ms'], 35)
        self.assertEqual(result['delivery']['over_30_ms'], 1)

    def test_rejects_truncation_and_missing_frames(self):
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            analyze(self.frames()[:40], 0, 100)
        frames = self.frames()
        del frames[50]
        with self.assertRaisesRegex(ValueError, 'Nonconsecutive'):
            analyze(frames, 0, 100)

    def test_excludes_query_boundaries(self):
        frames = self.frames()
        frames[0]['swap_end'] = 900000
        frames[-1]['swap_end'] = -1
        self.assertEqual(analyze(frames, 0, 100)['delivery']['max_ms'], 20)

    def test_preserves_processing_and_pacing_intervals(self):
        frames = self.frames()
        for row in frames:
            row['begin'] = row['input']-3000
            row['paced'] = row['input']-20
        result = analyze(frames, 0, 100)
        self.assertAlmostEqual(result['between_callbacks']['mean_ms'], 16.4)
        self.assertAlmostEqual(result['callback_to_paced']['mean_ms'], 2.98)


if __name__ == '__main__':
    unittest.main()
