import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from build_movie_native import capture, validate_ranges, EXPECTED_RANGES


class MovieNativeBuildTests(unittest.TestCase):
    def test_unsupported_disc_module_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported STDWTITL'):
            capture(bytes(26048))

    def test_missing_guards_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'coverage changed'):
            validate_ranges('int psx_overlay_dispatch(void) { return 1; }')

    def test_lost_or_expanded_coverage_is_rejected(self):
        def source(ranges):
            return '\n'.join(f'static const uint32_t psx_ov_static_ranges_{i:05d}[] = '
                             f'{{ 0x{a:08X}u, 0x{n:X}u }};' for i, (a, n) in enumerate(ranges))
        validate_ranges(source(EXPECTED_RANGES))
        for changed in (EXPECTED_RANGES-{(0x8780c, 0x34c)}, EXPECTED_RANGES|{(0x90000, 4)}):
            with self.assertRaisesRegex(ValueError, 'coverage changed'):
                validate_ranges(source(changed))

    def test_new_range_encoding_requires_review(self):
        with self.assertRaisesRegex(ValueError, 'range format'):
            validate_ranges('static const uint32_t psx_ov_static_ranges_00000[] = '
                            '{ 0x0008780Cu, 0x34Cu, 0x00090000u, 0x100u };')


if __name__ == '__main__':
    unittest.main()
