import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from measure_music_balance import measure, relative_db, report


class FakeNavigator:
    def __init__(self, fail=False):
        self.palette, self.frames, self.fail = 3, 0, fail
        self.calls = []

    def nav(self, op, **fields):
        self.calls.append((op, fields))
        if op == 'music':
            self.palette = fields.get('palette', self.palette)
            return dict(palette=self.palette, matched_notes=10)
        self.frames = fields.get('frames', self.frames)
        return dict(active=False, frames=self.frames, rms=[100, 50, 200, 0], peak=[400]*4)

    def where(self):
        return dict(mode=541, queued=0)

    def checkpoint(self, op, slot):
        return self.where()

    def until(self, sample, predicate, description):
        if self.fail:
            raise TimeoutError('interrupted capture')
        result = sample()
        assert predicate(result)
        return result


class MusicMeterTests(unittest.TestCase):
    def test_silence_and_db_are_explicit(self):
        self.assertAlmostEqual(relative_db(50, 100), -6.0206, places=4)
        self.assertIsNone(relative_db(0, 100))
        self.assertIsNone(relative_db(100, 0))
        text = report([dict(scene='test', palette=2, meter=dict(rms=[100, 50, 200, 0]))])
        self.assertIn('-6.0 dB', text)
        self.assertIn('+6.0 dB', text)

    def test_complete_and_interrupted_capture_restore_settings(self):
        for fail in (False, True):
            nav = FakeNavigator(fail)
            with tempfile.TemporaryDirectory() as directory, \
                    patch('measure_music_balance.Navigator', return_value=nav), \
                    patch('measure_music_balance.time.sleep'):
                output = Path(directory) / 'meter'
                if fail:
                    with self.assertRaises(TimeoutError):
                        measure(output, [('field', 1)], 1)
                else:
                    records = measure(output, [('field', 1)], 1)
                    self.assertEqual(len(records), 4)
                    self.assertEqual(json.loads((output/'measurements.json').read_text()), records)
                    self.assertTrue((output/'balance.md').exists())
                self.assertEqual(nav.palette, 3)
                self.assertEqual(nav.frames, 0)
                self.assertEqual(nav.calls[-2:], [('music-meter', dict(frames=0)), ('music', dict(palette=3))])


if __name__ == '__main__':
    unittest.main()
