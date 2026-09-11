import hashlib
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from upgrade_music_mix import upgrade


def fixture(instrument='drums'):
    wave = struct.pack('<II4h', 4, 1, -1200, 800, 1400, -900)
    data = (b'SHKMUS01' + struct.pack('<IIII', 44100, 1, 32, 1) + bytes(range(32))
            + struct.pack('<I', 16) + wave * 3)
    report = dict(sha256=hashlib.sha256(data).hexdigest(),
                  banks=[dict(samples=[dict(soundfont=instrument)])])
    return data, report


class MusicMixUpgradeTests(unittest.TestCase):
    def test_roles_added_without_changing_samples_loops_or_original_bank(self):
        for instrument, role in [('piano', 0), ('bass', 1), ('drums', 2)]:
            data, report = fixture(instrument)
            result, counts = upgrade(data, report)
            expected = b'SHKMUS02' + data[8:60] + struct.pack('<I', role) + data[60:]
            self.assertEqual(result, expected)
            self.assertEqual(sum(counts.values()), 1)
            self.assertEqual(counts[('melody', 'bass', 'percussion')[role]], 1)

    def test_mismatched_report_cannot_assign_roles(self):
        data, report = fixture()
        report['sha256'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'does not match'):
            upgrade(data, report)

    def test_truncation_trailing_bytes_and_invalid_loop_rejected(self):
        data, report = fixture()
        invalid_loop = bytearray(data)
        struct.pack_into('<I', invalid_loop, 64, 4)
        for invalid in (data[:-1], data+b'X', bytes(invalid_loop)):
            report['sha256'] = hashlib.sha256(invalid).hexdigest()
            with self.assertRaises(ValueError):
                upgrade(invalid, report)

    def test_report_count_mismatch_rejected(self):
        data, report = fixture()
        report['banks'][0]['samples'] = []
        with self.assertRaisesRegex(ValueError, 'routing report'):
            upgrade(data, report)


if __name__ == '__main__':
    unittest.main()
