import hashlib
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import generate_battle_motion_data as gen


class BattleMotionDataTests(unittest.TestCase):
    def test_rejects_unknown_revision(self):
        with self.assertRaises(ValueError):
            gen.generate(bytes(119632))

    def test_exact_guard_boundaries(self):
        data = bytearray(119632)
        lo, hi = 0x80083a54 - gen.BASE, 0x80084464 - gen.BASE
        struct.pack_into('<I', data, lo - 4, 0x11111111)
        struct.pack_into('<I', data, lo, 0x22222222)
        struct.pack_into('<I', data, hi - 4, 0x33333333)
        struct.pack_into('<I', data, hi, 0x44444444)
        wait_lo, wait_hi = 0x8008c230 - gen.BASE, 0x8008c2c4 - gen.BASE
        struct.pack_into('<I', data, wait_lo - 4, 0x55555555)
        struct.pack_into('<I', data, wait_lo, 0x66666666)
        struct.pack_into('<I', data, wait_hi - 4, 0x77777777)
        struct.pack_into('<I', data, wait_hi, 0x88888888)
        with patch.object(gen, 'MODULE_SHA256', hashlib.sha256(data).hexdigest()):
            header = gen.generate(data)
        self.assertEqual(header.count('0x00000000u'), (hi - lo + wait_hi - wait_lo) // 4 - 4)
        self.assertIn('0x22222222u', header)
        self.assertIn('0x33333333u', header)
        self.assertNotIn('0x11111111u', header)
        self.assertNotIn('0x44444444u', header)
        self.assertIn('0x66666666u', header)
        self.assertIn('0x77777777u', header)
        self.assertNotIn('0x55555555u', header)
        self.assertNotIn('0x88888888u', header)
