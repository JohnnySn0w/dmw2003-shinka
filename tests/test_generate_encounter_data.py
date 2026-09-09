import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import generate_encounter_data as gen


class EncounterDataTests(unittest.TestCase):
    def test_rejects_unknown_disc_revision(self):
        with self.assertRaises(ValueError):
            gen.generate(bytes(102040))

    def test_emits_only_countdown_guard_and_costs(self):
        data = bytes(102040)
        with patch.object(gen, 'FIELD_HASH', hashlib.sha256(data).hexdigest()):
            header = gen.generate(data)
        self.assertEqual(header.count('0x00000000u'), 157)
        self.assertIn('encounter_costs[] = {0,0,0,0,0,0}', header)
