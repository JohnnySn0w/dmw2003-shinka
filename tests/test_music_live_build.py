import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from build_music_live import MIX, RATE, level_target, lowpass, normalized, presence, reference_pitch, rms


class LiveMusicMixTests(unittest.TestCase):
    def test_reference_pitch_cancels_guest_transposition_at_normal_notes(self):
        for instrument, expected in [('piano', 60), ('clarinet', 60), ('bass', 48)]:
            for root in (31, 59.9765625, 81, 96):
                reference, ratio = reference_pitch(root, instrument)
                self.assertEqual(reference, expected)
                guest_step = 2 ** ((expected-root)/12)
                self.assertAlmostEqual(guest_step*ratio/65536, 1, delta=.00005)
                # The DS cutoff now stays at its configured reference cutoff;
                # a root 84 sample previously became 2 kHz at note 60.
                self.assertAlmostEqual(MIX['ds_cutoff_hz']*guest_step*ratio/65536, MIX['ds_cutoff_hz'], delta=.6)
        reference, ratio = reference_pitch(110, 'bass')
        actual_hz = 440*2**((reference-69)/12) * ratio/65536 * 2**((48-110)/12)
        self.assertAlmostEqual(actual_hz, 440*2**((48-69)/12), places=3)

    def test_source_balance_preserved_without_raising_drums(self):
        source = np.full(RATE, .35)
        self.assertAlmostEqual(level_target(source, 'clarinet'), .35)
        self.assertAlmostEqual(level_target(source, 'drums'), .22)
        self.assertLessEqual(level_target(np.ones(RATE), 'piano'), .5)

    def test_ds_melodic_filter_preserves_upper_band_without_brightening_drums(self):
        tone = np.sin(2*np.pi*9000*np.arange(RATE)/RATE)
        self.assertGreater(rms(lowpass(tone, MIX['ds_cutoff_hz']))/rms(tone), .9)
        self.assertLess(rms(lowpass(tone, MIX['ds_percussion_cutoff_hz']))/rms(tone), .4)

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
