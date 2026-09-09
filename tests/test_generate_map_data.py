import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import generate_map_data as gen


class MapDataTests(unittest.TestCase):
    def test_unknown_revision_is_rejected(self):
        with self.assertRaises(ValueError):gen.generate(bytes(100936))

    def test_guard_ranges_and_stage_map_are_emitted(self):
        data=bytes(100936)
        with patch.object(gen,'STATUS_HASH',hashlib.sha256(data).hexdigest()):
            text=gen.generate(data)
        self.assertEqual(text.count('0x00000000u'),sum((e-s)//4 for s,e in gen.RANGES))
        self.assertIn('map_stage_icons[] = {'+','.join(['0']*215)+'}',text)
