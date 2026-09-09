import hashlib
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import generate_evolution_data as gen
from evolution_hints import Requirement, ROOKIES


class EvolutionDataTests(unittest.TestCase):
    def setUp(self):
        self.exe = bytearray(0x40000)
        profile = 0x3ef5c - 0x10000 + 0x800
        for i in range(52):
            struct.pack_into('<H', self.exe, profile + i * 88, 100 + i)
            self.exe[profile + i * 88 + 0x55] = i + 1
        self.lab = bytearray(53504)
        for rookie in range(8):
            struct.pack_into('<6H', self.lab, 0x8f768 - 0x82cb0 + rookie * 192,
                             3, 108, 109, 110, 0, 0)
        self.rows = {name: [Requirement(i + 9, ((14, 600),), 13, 600) for i in range(44)]
                     for name in ROOKIES}

    def generate(self):
        with patch.object(gen, 'LAB_HASH', hashlib.sha256(self.lab).hexdigest()), \
             patch.object(gen, 'EXE_HASH', hashlib.sha256(self.exe).hexdigest()), \
             patch.object(gen, 'read_requirements', return_value=self.rows):
            return gen.generate(b'', self.lab, self.exe)

    def test_profile_mapping_and_no_thresholds_in_view_data(self):
        text = self.generate()
        self.assertIn('{108,109,110,0,0}', text)
        self.assertIn('{14,0,13}', text)
        self.assertNotIn('600', text)
        self.rows['Kotemon'][0] = Requirement(9, ((14, 5),), 13, 100)
        self.assertEqual(text, self.generate())

    def test_rejects_revisions_and_unknown_mappings(self):
        with patch.object(gen, 'read_requirements', return_value=self.rows):
            with self.assertRaises(ValueError):
                gen.generate(b'', self.lab, self.exe)
        self.rows['Kotemon'][0] = Requirement(8, (), 7, 5)
        with self.assertRaises(ValueError):
            self.generate()
        self.rows['Kotemon'][0] = Requirement(9, (), 7, 5)
        struct.pack_into('<H', self.lab, 0x8f768 - 0x82cb0, 4)
        with self.assertRaises(ValueError):
            self.generate()
