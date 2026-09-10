import io
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from music_export import (bank, decode_adpcm, encode_events, encode_vlq, export,
                          midi_events, sequences, unpack_pack, wav_bytes)


def sep(body, identity=0):
    return (b'pQES\0\0' + struct.pack('>HH', identity, 96) + bytes.fromhex('07a1200402')
            + struct.pack('>I', len(body)) + body)


def sample_bank():
    body = bytes((12, 6)) + bytes((0xf1,)) * 14 + bytes((12, 3)) + bytes(14)
    header = bytearray(0xc20)
    header[:4] = b'pBAV'
    struct.pack_into('<3I', header, 4, 7, 0, len(header) + len(body))
    struct.pack_into('<3H', header, 18, 1, 1, 1)
    header[24:26] = bytes((127, 64))
    # Sparse program numbers still use compact tone-table slots.
    header[32 + 5 * 16] = 1
    header[0x820:0x828] = bytes((0, 0, 127, 64, 60, 0, 0, 127))
    struct.pack_into('<4H', header, 0x830, 0x80ff, 0x5fc7, 5, 1)
    struct.pack_into('<H', header, 0xa22, len(body) // 8)
    return bytes(header), body


class MusicExportTests(unittest.TestCase):
    def test_pack_extents(self):
        self.assertEqual(unpack_pack(struct.pack('<2I', 8, 11) + b'abcdef'), [b'abc', b'def'])
        for data in (b'', bytes(4), struct.pack('<I', 9), struct.pack('<2I', 8, 8),
                     struct.pack('<2I', 8, 20) + b'x'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                unpack_pack(data)

    def test_seq_tempo_conversion_running_status_and_duration(self):
        body = bytes.fromhex('00c00500903c40603c0000ff5103d09030903e20003e0000ff2f00')
        meta, midi = sequences(sep(body))[0]
        self.assertAlmostEqual(meta['seconds_one_pass'], .625)
        self.assertEqual(meta['program_usage'][0]['notes'], 2)
        self.assertEqual(meta['program_usage'][0]['program'], 5)
        self.assertEqual(midi[:14], b'MThd' + struct.pack('>I3H', 6, 0, 1, 96))
        self.assertEqual(struct.unpack_from('>I', midi, 18)[0], len(midi) - 22)
        converted = midi_events(midi[22:])
        self.assertEqual(converted[2:], midi_events(body, psx=True))
        self.assertIn(bytes.fromhex('ff510303d090'), midi)

    def test_controller_and_sysex_preservation(self):
        body = bytes.fromhex('00b0631400621000067f00f0030102f700ff2f00')
        events = midi_events(body)
        self.assertEqual(midi_events(encode_events(events)), events)
        self.assertEqual([r['controller'] for r in sequences(sep(body))[0][0]['controllers']], [99, 98, 6])
        for value in (0, 127, 128, 16384, 0x0fffffff):
            eot = encode_vlq(value) + bytes.fromhex('ff2f00')
            self.assertEqual(midi_events(eot)[0]['tick'], value)

    def test_reject_malformed_score(self):
        for body in (b'', bytes.fromhex('003c40'), bytes.fromhex('00903c'),
                     bytes.fromhex('8080808000ff2f00'), bytes.fromhex('00ff2f0100'),
                     bytes.fromhex('00ff2f0000'), bytes.fromhex('00f103'),
                     bytes.fromhex('00ff51030000')):
            with self.subTest(body=body), self.assertRaises(ValueError):
                midi_events(body)
        with self.assertRaises(ValueError): sequences(sep(bytes.fromhex('00ff2f00'))[:-1])
        with self.assertRaises(ValueError): sequences(b'pQES\0\1')

    def test_adpcm_sign_prediction_and_loop(self):
        pcm, loop, used = decode_adpcm(bytes((12, 1)) + bytes((0xf1,)) * 14)
        self.assertEqual(pcm, [1, -1] * 14); self.assertIsNone(loop); self.assertEqual(used, 16)
        pcm, _, _ = decode_adpcm(bytes((0x10, 1, 1)) + bytes(13))
        self.assertEqual(pcm[:3], [4096, 3840, 3600])
        _, body = sample_bank()
        pcm, loop, used = decode_adpcm(body + bytes((255,)) * 16)
        self.assertEqual((len(pcm), loop, used), (56, [0, 56], 32))
        for data in (b'', bytes(15), bytes(16), bytes((0x50, 1)) + bytes(14),
                     bytes((13, 1)) + bytes(14), bytes((0, 8)) + bytes(14)):
            with self.subTest(data=data), self.assertRaises(ValueError): decode_adpcm(data)

    def test_bank_mapping_and_wave_loop(self):
        header, body = sample_bank(); meta, waves = bank(header, body)
        self.assertEqual(meta['programs'][0]['program'], 5)
        self.assertEqual(meta['programs'][0]['tones'][0]['sample'], 1)
        self.assertEqual(meta['samples'][0]['loop_frames'], [0, 56])
        self.assertEqual(meta['samples'][0]['consumed_adpcm_bytes'], 32)
        wav = waves[0]
        self.assertEqual(struct.unpack_from('<I', wav, 4)[0], len(wav) - 8)
        with wave.open(io.BytesIO(wav)) as reader:
            self.assertEqual((reader.getframerate(), reader.getnframes(), reader.getnchannels()), (44100, 56, 1))
            self.assertEqual(struct.unpack('<2h', reader.readframes(2)), (1, -1))
        smpl = wav.index(b'smpl')
        self.assertEqual(struct.unpack_from('<2I', wav, smpl + 8 + 36 + 8), (0, 55))
        for index, value in ((18, 129), (0xa22, 9), (0x836, 2), (0x20 + 80, 17)):
            broken = bytearray(header); broken[index] = value
            with self.subTest(index=index), self.assertRaises(ValueError): bank(broken, body)

    def test_export_preserves_inputs_and_refuses_overwrite(self):
        header, body = sample_bank(); score = sep(bytes.fromhex('00c00500903c40013c0000ff2f00'))
        score += sep(bytes.fromhex('00c07f00903c40013c0000ff2f00'), identity=1)[6:]
        mp = struct.pack('<2I', 8, 8 + len(header)) + header + score
        mv = struct.pack('<I', 4) + body
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); a = root / 'MP.BIN'; b = root / 'MV.BIN'
            a.write_bytes(mp); b.write_bytes(mv); dest = root / 'export'
            report = export(a, b, dest)
            self.assertEqual((a.read_bytes(), b.read_bytes()), (mp, mv))
            self.assertEqual(len(report['bank']['samples']), 1)
            self.assertEqual(report['sequences'][0]['unmapped_programs'], [])
            self.assertEqual(report['sequences'][1]['unmapped_programs'], [127])
            self.assertTrue((dest / 'sequence-000.mid').exists())
            with self.assertRaises(ValueError): export(a, b, dest)


if __name__ == '__main__': unittest.main()
