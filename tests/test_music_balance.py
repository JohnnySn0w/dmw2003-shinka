import copy
from functools import partial
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from balance_music_arrangements import RATE, active_mask, eq_settings, measure, peak_gain, spectrum
from serve_music_arrangements import MixerHandler, Profiles


class BalanceTests(unittest.TestCase):
    def tone(self, hz, seconds=2):
        signal = .1*np.sin(2*np.pi*hz*np.arange(RATE*seconds)/RATE)
        return np.column_stack((signal, signal)).astype('<f4')

    def test_windowed_k_measurement_agrees_with_time_domain_for_steady_tone(self):
        audio = self.tone(1000)
        filters = ('biquad=b0=1.53512485958697:b1=-2.69169618940638:b2=1.19839281085285:'
                   'a0=1:a1=-1.69065929318241:a2=0.73248077421585,'
                   'biquad=b0=1:b1=-2:b2=1:a0=1:a1=-1.99004745483398:a2=0.99007225036621')
        raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ar', str(RATE),
                                       '-ac', '2', '-i', '-', '-af', filters, '-f', 'f32le', '-'],
                                      input=audio.tobytes())
        filtered = np.frombuffer(raw, '<f4').reshape(-1, 2)[RATE//2:]
        expected = -.691 + 10*np.log10(np.mean(np.sum(filtered**2, axis=1)))
        self.assertAlmostEqual(measure(spectrum(audio))['db'], expected, delta=.04)

    def test_silence_does_not_pull_active_phrase_level_down(self):
        tone = self.tone(1000)
        padded = np.concatenate((np.zeros_like(tone), tone, np.zeros_like(tone)))
        self.assertAlmostEqual(measure(spectrum(tone))['db'], measure(spectrum(padded))['db'], delta=.5)
        power = spectrum(np.zeros_like(tone))
        self.assertFalse(active_mask(power).any())
        self.assertEqual(measure(power)['active_blocks'], 0)

    def test_eq_bounded_and_missing_bands_not_boosted(self):
        ref = dict(active_blocks=3, warmth=-1, presence=-3)
        current = dict(active_blocks=3, warmth=-30, presence=-80)
        self.assertEqual(eq_settings(ref, current, 'flute'), dict(warmth=2., presence=0.))
        self.assertEqual(eq_settings(ref, current, 'original'), dict(warmth=0., presence=0.))
        self.assertEqual(eq_settings(ref, current, 'triangle')['warmth'], 1.)

    def test_master_retains_headroom_with_transient(self):
        audio = self.tone(1000)
        audio[100] = 4
        gain = peak_gain(audio)
        self.assertLessEqual(float(np.max(np.abs(audio*gain))), .790001)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.catalog = dict(identity='source-a', tracks=[dict(id='BGM018-000',
                            palettes=dict(sampled=dict(parts=[dict(part=1)])))])
        self.store = Profiles(self.directory, self.catalog)
        self.request = dict(identity='source-a', revision=0, key='BGM018-000/sampled',
                            values={'1': dict(gain=-2, warmth=.5, presence=1)})

    def tearDown(self):
        self.temporary.cleanup()

    def test_roundtrip_and_stale_write_rejected(self):
        self.store.save(self.request)
        self.assertEqual(Profiles(self.directory, self.catalog).state['values'][self.request['key']], self.request['values'])
        with self.assertRaises(FileExistsError):
            self.store.save(self.request)
        changed = {**self.catalog, 'identity': 'another-render'}
        with self.assertRaises(ValueError):
            Profiles(self.directory, changed)

    def test_bad_values_and_source_identity_are_not_saved(self):
        for value in (13, float('nan'), float('inf'), True, '2'):
            request = copy.deepcopy(self.request)
            request['values']['1']['gain'] = value
            with self.assertRaises(ValueError):
                self.store.save(request)
        with self.assertRaises(ValueError):
            self.store.save({**self.request, 'identity': 'other'})
        self.assertFalse(self.store.path.exists())

    def test_failed_disk_write_does_not_advance_revision(self):
        with patch.object(Path, 'replace', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                self.store.save(self.request)
        self.assertEqual(self.store.state['revision'], 0)
        self.assertFalse(self.store.path.exists())
        self.store.save(self.request)
        self.assertEqual(self.store.state['revision'], 1)

    def test_http_auth_revision_and_media_range(self):
        (self.directory/'sample.wav').write_bytes(b'0123456789')
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(MixerHandler, directory=str(self.directory)))
        server.profiles = self.store
        server.expected_host = f'127.0.0.1:{server.server_port}'
        server.token = 'test-token'
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        connection = HTTPConnection('127.0.0.1', server.server_port)
        try:
            connection.request('GET', '/sample.wav', headers={'Range': 'bytes=2-5'})
            response = connection.getresponse()
            self.assertEqual(response.status, 206)
            self.assertEqual(response.read(), b'2345')
            for headers, expected in [({}, 403), ({'X-Mixer-Token':server.token, 'Origin':'https://example.com'}, 403),
                                      ({'X-Mixer-Token':server.token}, 200), ({'X-Mixer-Token':server.token}, 409)]:
                connection.request('POST', '/api/profile', json.dumps(self.request), headers)
                response = connection.getresponse()
                self.assertEqual(response.status, expected)
                response.read()
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
