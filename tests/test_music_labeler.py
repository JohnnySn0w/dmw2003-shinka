import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from label_music_stems import LabelStore, ThreadingHTTPServer, family_identity, handler_for, identity_key, load_catalog


def fixture(root):
    library = root/'library'
    folder = library/'BGM018-000'
    folder.mkdir(parents=True)
    native = root/'native'
    native.mkdir()
    part = dict(part=1, programs=[0], samples=[1, 2], file='full.wav', audition='short.wav')
    manifest = dict(bank='BGM018', sequence=0, source_sha256={'source': 'hash'},
                    context=dict(title='Badlands', scene='Desert'), parts=[part])
    for directory in (folder, native):
        for name in ('full.wav', 'short.wav'):
            (directory/name).write_bytes(b'RIFFabcdefghijklmnop')
    (library/'batch.json').write_text(json.dumps(dict(tracks=[dict(id='BGM018-000', manifest=manifest)])))
    (native/'stems.json').write_text(json.dumps(manifest))
    (native/'identifications.json').write_text(json.dumps(dict(bank='BGM018', source_sha256={'source': 'hash'},
        parts={'1': dict(programs=[0], samples=[1, 2], instrument='piano', user_description='sounds like a piano',
                         status='user-identified')})))
    return library, native


class MusicLabelerTests(unittest.TestCase):
    def test_native_matching_and_seeds_follow_identity_not_display_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            library, native = fixture(Path(tmp))
            tracks, parts, _, seeds = load_catalog(library, {'BGM018-000': native})
            key = next(iter(parts))
            self.assertEqual(parts[key]['sources'], ['native', 'offline'])
            self.assertEqual(seeds[key]['instrument'], 'piano')
            self.assertEqual(tracks[0]['scene'], 'Desert')
            path = library/'batch.json'
            data = json.loads(path.read_text())
            data['tracks'][0]['manifest']['parts'][0]['part'] = 99
            path.write_text(json.dumps(data))
            self.assertIn(key, load_catalog(library, {'BGM018-000': native})[1])
            data['tracks'][0]['manifest']['source_sha256'] = {'source': 'different'}
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'identity'):
                load_catalog(library, {'BGM018-000': native})

    def test_labels_survive_restart_seeding_and_conflicting_tabs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library, native = fixture(root)
            _, parts, _, seeds = load_catalog(library, {'BGM018-000': native})
            key = next(iter(parts))
            store = LabelStore(root/'labels.json', parts, seeds)
            payload = dict(key=key, revision=1, instrument='upright piano', confidence='tentative',
                           notes='bright attack', audio_source='native')
            store.save(payload)
            with self.assertRaises(FileExistsError):
                store.save(payload)
            reloaded = LabelStore(root/'labels.json', parts, seeds)
            self.assertEqual(reloaded.snapshot()['labels'][key]['instrument'], 'upright piano')
            self.assertEqual(reloaded.snapshot()['labels'][key]['revision'], 2)
            self.assertEqual(reloaded.snapshot()['labels'][key]['audio_source'], 'native')

    def test_invalid_or_failed_write_does_not_change_saved_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library, native = fixture(root)
            _, parts, _, seeds = load_catalog(library, {'BGM018-000': native})
            key = next(iter(parts))
            store = LabelStore(root/'labels.json', parts, seeds)
            before = (root/'labels.json').read_bytes()
            payload = dict(key=key, revision=1, instrument='piano', confidence='tentative', notes='', audio_source='native')
            for field, value in [('key', 'bad'), ('confidence', 'bad'), ('audio_source', 'bad'),
                                 ('instrument', 'x'*161), ('notes', None), ('revision', True)]:
                with self.assertRaises(ValueError):
                    store.save(dict(payload, **{field: value}))
            with patch.object(Path, 'replace', side_effect=OSError('disk error')):
                with self.assertRaises(OSError):
                    store.save(payload)
            self.assertEqual((root/'labels.json').read_bytes(), before)
            self.assertEqual(store.snapshot()['labels'][key]['revision'], 1)

    def test_audio_paths_cannot_escape_the_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            library, _ = fixture(Path(tmp))
            path = library/'batch.json'
            data = json.loads(path.read_text())
            data['tracks'][0]['manifest']['parts'][0]['file'] = '../batch.json'
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'outside'):
                load_catalog(library, {})

    def test_http_save_readback_ranges_and_cross_origin_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library, native = fixture(root)
            tracks, parts, audio, seeds = load_catalog(library, {'BGM018-000': native})
            store = LabelStore(root/'labels.json', parts, seeds)
            handler = handler_for(tracks, audio, store, 'test-token')
            handler.log_message = lambda *args: None
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f'http://127.0.0.1:{server.server_port}'
                with urlopen(base+'/api/catalog') as r:
                    catalog = json.load(r)
                self.assertEqual(catalog['token'], 'test-token')
                key = next(iter(parts))
                request = Request(base+f'/audio/{key}/native/full', headers={'Range': 'bytes=4-7'})
                with urlopen(request) as r:
                    self.assertEqual(r.status, 206)
                    self.assertEqual(r.read(), b'abcd')
                payload = json.dumps(dict(key=key, revision=1, instrument='Piano', confidence='confident',
                                          notes='test', audio_source='native')).encode()
                headers = {'X-Label-Token':'test-token', 'Origin':base}
                with urlopen(Request(base+'/api/labels', data=payload, headers=headers)) as r:
                    self.assertEqual(json.load(r)['revision'], 2)
                for bad in ({}, dict(headers, Origin='https://example.com')):
                    with self.assertRaises(HTTPError) as raised:
                        urlopen(Request(base+'/api/labels', data=payload, headers=bad))
                    self.assertEqual(raised.exception.code, 403)
                with urlopen(base+'/api/labels') as r:
                    self.assertEqual(json.load(r)['labels'][key]['instrument'], 'Piano')
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_sequence_and_sample_sets_are_part_of_label_identity(self):
        m = dict(bank='bank', sequence=0, source_sha256={'source': 'hash'})
        p = dict(programs=[0], samples=[2, 1])
        key = identity_key(family_identity(m, p))
        self.assertEqual(key, identity_key(family_identity(m, dict(p, samples=[1, 2]))))
        self.assertNotEqual(key, identity_key(family_identity(dict(m, sequence=1), p)))
        self.assertNotEqual(key, identity_key(family_identity(m, dict(p, samples=[1]))))


if __name__ == '__main__':
    unittest.main()
