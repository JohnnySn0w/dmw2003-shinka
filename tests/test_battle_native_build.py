import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from build_battle_native import capture, validate_ranges


class BattleNativeBuildTests(unittest.TestCase):
    def test_unsupported_module_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported FIGHTSTG'):
            capture(bytes(137968))

    def test_missing_guards_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'coverage changed'):
            validate_ranges('int psx_overlay_dispatch(void) { return 1; }')

    def test_unreviewed_coverage_is_rejected(self):
        source = 'static const uint32_t psx_ov_static_ranges_00000[] = { 0x00085110u, 0x10000u };'
        with self.assertRaisesRegex(ValueError, 'coverage changed'):
            validate_ranges(source)

    def test_new_range_encoding_requires_review(self):
        source = 'static const uint32_t psx_ov_static_ranges_00000[] = { 0x00085110u, 0x800u, 0x00090000u, 0x100u };'
        with self.assertRaisesRegex(ValueError, 'range format'):
            validate_ranges(source)


if __name__ == '__main__':
    unittest.main()
