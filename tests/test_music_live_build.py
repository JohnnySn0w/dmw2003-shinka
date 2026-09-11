import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from build_music_live import MIX, RATE, level_target, lowpass, normalized, presence, rms


class LiveMusicMixTests(unittest.TestCase):
    def test_source_balance_preserved_without_raising_drums(self):
        source = np.full(RATE, .35)
        self.assertAlmostEqual(level_target(source, 'clarinet'), .35)
        self.assertAlmostEqual(level_target(source, 'drums'), .22)
        self.assertLessEqual(level_target(np.ones(RATE), 'piano'), .5)

    def test_presence_lifts_upper_register_without_boosting_percussion(self):
        t = np.arange(RATE)/RATE
        low = np.sin(2*np.pi*220*t)
        high = np.sin(2*np.pi*6000*t)
        self.assertLess(rms(presence(low, 'piano'))/rms(low), 1.02)
        self.assertGreater(rms(presence(high, 'piano'))/rms(high), 1.35)
        np.testing.assert_array_equal(presence(high, 'drums'), high)
        np.testing.assert_array_equal(presence(low, 'bass'), low)

    def test_hybrid_recovers_blend_loss_and_retains_peak_headroom(self):
        t = np.arange(RATE)/RATE
        a = .3*np.sin(2*np.pi*440*t)
        b = -.3*np.sin(2*np.pi*440*t)
        ds = normalized(lowpass(.7*a+.3*b, 8000), .3).astype(float)/32767
        self.assertAlmostEqual(rms(ds), .3, places=4)
        spike = np.zeros(RATE); spike[10] = 1
        pcm = normalized(spike, .5).astype(float)/32767
        self.assertLessEqual(np.max(np.abs(pcm)), MIX['peak_ceiling']+1/32767)


if __name__ == '__main__':
    unittest.main()
