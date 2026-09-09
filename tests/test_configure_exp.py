import hashlib
import struct
import sys
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import configure_exp as exp


class ExpTests(unittest.TestCase):
    def fixture(self, value=7):
        data = bytearray(exp.TABLE + exp.ROWS * 12)
        for i in range(exp.ROWS):
            struct.pack_into('<III', data, exp.TABLE + i * 12, 3, value, 23)
        return bytes(data)

    def test_factors_change_only_normal_exp(self):
        data = self.fixture()
        with patch.object(exp, 'OVERLAY_SHA256', hashlib.sha256(data).hexdigest()):
            for factor in (1, 2, 3, 4):
                changed = bytearray(data)
                for offset, old, new in exp.exp_patches(data, 123, factor):
                    offset -= 123 * 2048
                    self.assertEqual(changed[offset:offset + 4], old)
                    self.assertLessEqual(offset % 2048 + 4, 2048)
                    changed[offset:offset + 4] = new
                for i in range(exp.ROWS):
                    self.assertEqual(struct.unpack_from('<III', changed, exp.TABLE + i * 12),
                                     (3, 7 * factor, 23))

    def test_reject_revision_and_overflow(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            exp.exp_patches(self.fixture(), 0, 2)
        data = self.fixture(0x7FFFFFFF // 6)
        with patch.object(exp, 'OVERLAY_SHA256', hashlib.sha256(data).hexdigest()):
            with self.assertRaisesRegex(ValueError, 'overflow'):
                exp.exp_patches(data, 0, 4)

    def test_preserve_other_mods_and_disable(self):
        original = '''format_version = 2
[[package]]
id = "another.mod"
version = "1.0.0"
[[feature]]
package_id = "another.mod"
id = "music"
enabled = true
[feature.values]
choice = "original"
'''
        first = exp.select_feature(original, 3)
        updated = tomllib.loads(exp.select_feature(first, 1))
        self.assertEqual(updated['feature'][0], tomllib.loads(original)['feature'][0])
        self.assertEqual(len(updated['package']), 2)
        self.assertEqual(len(updated['feature']), 2)
        self.assertFalse(updated['feature'][1]['enabled'])
        self.assertEqual(updated['feature'][1]['values']['multiplier'], '1')

    def test_reject_legacy_state(self):
        with self.assertRaises(ValueError):
            exp.select_feature('format_version = 1', 2)
