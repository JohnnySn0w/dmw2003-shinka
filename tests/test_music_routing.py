import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from music_routing import ROUTING, bank_overrides


class MusicRoutingTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads(ROUTING.read_text())
        self.meta = dict(inputs=self.profile['banks']['BGM018']['inputs'], bank=dict(
            samples=[dict(id=3), dict(id=11)],
            programs=[dict(program=1, tones=[dict(sample=3), dict(sample=3)]),
                      dict(program=8, tones=[dict(sample=11)])]))

    def test_reviewed_badlands_roles_and_unrelated_bank(self):
        routes = bank_overrides('BGM018', self.meta, self.profile)
        self.assertEqual(routes['3']['soundfont'], 'strings')
        self.assertEqual(routes['3']['chip'], 'pulse')
        self.assertEqual(routes['11']['soundfont'], 'bass')
        self.assertEqual(bank_overrides('BATL00', self.meta, self.profile), {})

    def test_changed_source_or_owners_are_rejected(self):
        meta = copy.deepcopy(self.meta)
        meta['inputs']['MPBGM018.BIN'] = '0' * 64
        with self.assertRaises(ValueError):
            bank_overrides('BGM018', meta, self.profile)
        meta = copy.deepcopy(self.meta)
        meta['bank']['programs'].append(dict(program=9, tones=[dict(sample=3)]))
        with self.assertRaises(ValueError):
            bank_overrides('BGM018', meta, self.profile)

    def test_invalid_sample_timbre_or_reason_is_rejected(self):
        for field, value in [('soundfont', 'missing'), ('chip', 'noise'), ('reason', '')]:
            profile = copy.deepcopy(self.profile)
            profile['banks']['BGM018']['samples']['3'][field] = value
            with self.assertRaises(ValueError):
                bank_overrides('BGM018', self.meta, profile)
        meta = copy.deepcopy(self.meta)
        meta['bank']['samples'] = [dict(id=3)]
        with self.assertRaises(ValueError):
            bank_overrides('BGM018', meta, self.profile)


if __name__ == '__main__':
    unittest.main()
