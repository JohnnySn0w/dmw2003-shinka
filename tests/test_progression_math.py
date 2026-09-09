import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from progression_math import rookie_threshold, dv_threshold, dv_award


class ProgressionTests(unittest.TestCase):
    def test_observed_early_kumamon_thresholds(self):
        self.assertEqual(rookie_threshold(2, 10), 13)
        self.assertEqual(rookie_threshold(5, 10), 195)
        self.assertEqual(rookie_threshold(99, 10), 973789)

    def test_natural_limit_boundary(self):
        self.assertEqual([dv_threshold(l, 60) for l in (59, 60, 61)], [580, 590, 640])
        self.assertEqual(dv_threshold(99), 980)

    def test_observed_kunemon_and_level_denominator(self):
        self.assertEqual(dv_award(1, 5), 2)
        self.assertEqual(dv_award(1, 10), 1)
        self.assertEqual(dv_award(20, 50, skill_level=60, natural_limit=60), 4)
        self.assertEqual(dv_award(20, 99, skill_level=60, natural_limit=60), 4)

    def test_participation_rounding_and_caps(self):
        self.assertEqual(dv_award(3, 4, participants=2), 4)
        self.assertEqual(dv_award(3, 4, participants=3), 2)
        self.assertEqual(dv_award(100, 1), 10)
        self.assertEqual(dv_award(100, 1, skill_level=60, natural_limit=60), 50)
