import copy
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from arrange_labelled_music import completed_tracks, route, write_audio
from fetch_labelled_instruments import local
from label_music_stems import family_identity, identity_key


class LabelledArrangementsTests(unittest.TestCase):
    def fixture(self):
        manifest = dict(bank='BGM018', sequence=0, source_sha256={'MP': 'abc'},
                        parts=[dict(part=1, programs=[0], samples=[1])])
        identity = family_identity(manifest, manifest['parts'][0])
        labels = {identity_key(identity): dict(identity=identity, instrument='flute', confidence='tentative')}
        return dict(tracks=[dict(id='BGM018-000', manifest=manifest)]), labels

    def test_only_complete_matching_tracks_are_selected(self):
        batch, labels = self.fixture()
        self.assertEqual(len(completed_tracks(batch, labels)[0]), 1)
        changed = copy.deepcopy(batch)
        changed['tracks'][0]['manifest']['source_sha256']['MP'] = 'changed'
        complete, skipped = completed_tracks(changed, labels)
        self.assertFalse(complete)
        self.assertEqual(len(skipped), 1)
        next(iter(labels.values()))['instrument'] = '  '
        self.assertFalse(completed_tracks(batch, labels)[0])

    def test_reject_mismatched_identity_under_valid_key(self):
        batch, labels = self.fixture()
        next(iter(labels.values()))['identity']['programs'] = [99]
        with self.assertRaises(ValueError):
            completed_tracks(batch, labels)

    def test_listener_labels_are_not_rewritten(self):
        label = dict(instrument='piano synth', notes='could be a suite of violins/strings', confidence='tentative')
        original = copy.deepcopy(label)
        self.assertEqual(route(label), 'violin')
        self.assertEqual(label, original)
        self.assertEqual(route(dict(instrument='sfx')), 'original')
        self.assertEqual(route(dict(instrument='metal triangle')), 'triangle')
        self.assertEqual(route(dict(instrument='santur')), 'psaltery')
        self.assertEqual(route(dict(instrument='piano synth', notes='violin motion, not the actual string sound')), 'fm-piano')
        with self.assertRaises(ValueError):
            route(dict(instrument='new unreviewed instrument'))

    def test_reject_clipping_and_nonfinite_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'test.wav'
            for value in (1.01, np.nan, np.inf):
                with self.assertRaises(ValueError):
                    write_audio(path, np.full((100, 2), value))
            self.assertFalse(path.exists())
            write_audio(path, np.zeros((100, 2)))
            self.assertTrue(path.exists())

    def test_download_paths_stay_inside_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(local(root, 'instrument/a.wav'), root/'instrument/a.wav')
            with self.assertRaises(ValueError):
                local(root, '../escape.wav')


if __name__ == '__main__':
    unittest.main()
