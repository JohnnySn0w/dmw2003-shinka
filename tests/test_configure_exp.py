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

    def test_dv_scales_final_argument_without_changing_other_registers(self):
        data = bytearray(0x1400)
        struct.pack_into('<4I', data, 0x1388, 0x8E030020, 0, 0x0060F809, 0x00403021)
        with patch.object(exp, 'OVERLAY_SHA256', hashlib.sha256(data).hexdigest()):
            for factor in (2, 3, 4):
                offset, old, new = exp.dv_patches(data, 123, factor)[0]
                self.assertEqual(offset, 123 * 2048 + 0x1388)
                words = struct.unpack('<4I', new)
                self.assertEqual(words[0], 0x8E030020)
                self.assertEqual(words[2], 0x0060F809)
                # Execute the two changed MIPS ALU slots around the call.
                # Exhaust both original DV cap ranges, including minimum 1.
                for award in range(1, 51):
                    registers = list(range(32))
                    registers[0], registers[2] = 0, award
                    original_registers = registers[:]
                    for word in (words[1], words[3]):
                        rs, rt, rd = (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
                        if word == 0:
                            continue
                        if word & 63 == 0:
                            registers[rd] = registers[rt] << ((word >> 6) & 31)
                        elif word & 63 == 33:
                            registers[rd] = registers[rs] + registers[rt]
                        else:
                            self.fail('Unexpected instruction in DV patch')
                    self.assertEqual(registers[6], award * factor)
                    registers[6] = original_registers[6]
                    self.assertEqual(registers, original_registers)

    def test_dv_setting_preserves_normal_exp(self):
        state = exp.select_feature('', 3)
        state = exp.select_feature(state, 3, 'dv-exp')
        state = exp.select_feature(state, 1, 'dv-exp')
        values = {f['id']: f for f in tomllib.loads(state)['feature']}
        self.assertTrue(values['battle-exp']['enabled'])
        self.assertEqual(values['battle-exp']['values']['multiplier'], '3')
        self.assertFalse(values['dv-exp']['enabled'])
