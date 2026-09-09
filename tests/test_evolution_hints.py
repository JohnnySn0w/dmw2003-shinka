import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import struct

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import evolution_hints as eh


class EvolutionHintTests(unittest.TestCase):
    def test_thresholds_and_unrevealed_forms_do_not_leak(self):
        req = eh.Requirement(99, ((10, 40), (20, 99)), 13, 160)
        text = ' '.join(eh.hints(req, {10: 'Greymon'}))
        self.assertIn('Greymon', text)
        self.assertIn('other evolution paths', text)
        self.assertIn('machines', text)
        self.assertFalse(any(ch.isdigit() for ch in text))
        changed = eh.Requirement(99, ((10, 5), (20, 20)), 13, 300)
        self.assertEqual(eh.hints(req, {10: 'Greymon'}), eh.hints(changed, {10: 'Greymon'}))

    def test_two_form_training_and_no_extra_requirement(self):
        req = eh.Requirement(99, ((10, 5), (20, 5)), 0, 1)
        self.assertEqual(eh.hints(req, {10: 'ExVeemon', 20: 'Stingmon'}), [
            'Deepen your mastery of ExVeemon.', 'Deepen your mastery of Stingmon.'])
        self.assertEqual(eh.hints(req, {}), ['Explore other evolution paths with your partner.'])

    def test_rookie_tables_are_independent_and_revision_guarded(self):
        data = bytearray(eh.TABLE + 8 * eh.ROWS * 16)
        for i in range(8 * eh.ROWS):
            struct.pack_into('<8H', data, eh.TABLE + i * 16, 9, 0, 0, 1, 0, 1, 7, i + 1)
        with self.assertRaises(ValueError):
            eh.read_requirements(data)
        with patch.object(eh, 'OVERLAY_SHA256', hashlib.sha256(data).hexdigest()):
            tables = eh.read_requirements(data)
        self.assertEqual(len(tables), 8)
        self.assertEqual(tables['Kumamon'][0].extra_value, 45)
        self.assertEqual(eh.hints(tables['Kumamon'][0], {}), ['Grow stronger alongside your partner.'])
