import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from music_context import CATALOG, listening_notes, track_context


class MusicContextTests(unittest.TestCase):
    def test_auditions_have_matching_scene_and_unknown_score_is_not_mislabeled(self):
        for name in ('bgm001-audition.json', 'bgm001-ds.json'):
            profile = json.loads(CATALOG.with_name(name).read_text())
            context = track_context(profile['midi_sha256'])
            self.assertEqual(context['id'], 'BGM001:000')
            self.assertEqual(context['title'], 'Asuka City')
            self.assertFalse(context['runtime_scene_verified'])
            self.assertIn('Instrumental / Sampled', listening_notes(context, 'soundfont'))
        self.assertIsNone(track_context('0' * 64))
        self.assertIn('Unidentified track', listening_notes(None, 'ds'))

    def test_duplicate_fingerprints_do_not_choose_a_scene_arbitrarily(self):
        row = json.loads(CATALOG.read_text())['tracks'][0]
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / 'catalog.json'
            catalog.write_text(json.dumps({'tracks': [row, row]}))
            self.assertIsNone(track_context(row['midi_sha256'], catalog))


if __name__ == '__main__':
    unittest.main()
