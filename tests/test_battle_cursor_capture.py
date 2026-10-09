import json
from pathlib import Path
import struct
import tempfile
import unittest

import numpy as np

from tools.check_battle_cursor_capture import check, cursor_tiles


class CursorCaptureTests(unittest.TestCase):
    def setUp(self):
        self.span = dict(x=0, y=244, w=156, h=12,
                         hex=''.join(f'{(x//12+1) | (7<<5) | (20<<10):04x}'
                                     for _ in range(12) for x in range(156)))
        self.tiles = cursor_tiles([self.span])

    def fixture(self, path, margin=53, stray=None, empty=False):
        copies = []
        with path.open('wb') as stream:
            stream.write(b'SHCAP001')
            for frame in range(3):
                im = np.zeros((240, 320+margin*2, 4), dtype=np.uint8)
                im[:, :, 3] = 255
                tile = 12 if frame == 1 else frame
                patch = self.tiles[tile]
                if margin == 0:
                    patch = ((patch*31+127)//255)*8
                if not empty:
                    im[69:81, 14:26, :3] = patch[:, :, ::-1]
                if frame == stray:
                    im[69:81, 14+margin:26+margin, :3] = patch[:, :, ::-1]
                stream.write(struct.pack('<8I', frame, im.shape[1], 240, 0x600, 0,
                                         int(margin > 0), 0, 65535))
                stream.write(im.tobytes())
                for band in (0, 256):
                    copies.append(dict(frame=frame, op='0x80', w=[
                        '0x80000000', hex((244<<16) | (tile*12)),
                        hex(((69+band)<<16) | 14), '0x000c000c']))
        return copies

    def test_complete_wide_cycle_and_original_control(self):
        with tempfile.TemporaryDirectory() as temp:
            for margin in (0, 53):
                path = Path(temp)/'frames.bin'
                copies = self.fixture(path, margin)
                result = check(path, copies, self.tiles, margin)
                self.assertTrue(result['passed'])
                self.assertEqual(result['visible_tiles'], [0, 2, 12])
                self.assertEqual(result['framebuffer_bands'], [0, 256])

    def test_single_bad_clearing_frame_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'frames.bin'
            copies = self.fixture(path, stray=1)
            result = check(path, copies, self.tiles)
            self.assertFalse(result['passed'])
            self.assertEqual(result['old_anchor_matches'],
                             [dict(frame=1, x=67, y=69, tile=12)])

    def test_missing_or_unrecognized_evidence_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'frames.bin'
            copies = self.fixture(path, empty=True)
            with self.assertRaisesRegex(ValueError, 'Missing'):
                check(path, copies, self.tiles)
            copies = self.fixture(path)
            for bad in ([], [dict(copies[0], frame=99)],
                        [dict(copies[0], w=['0x80000000', '0x00f4009c',
                                           '0x0045000e', '0x000c000c'])]):
                with self.assertRaises(ValueError):
                    check(path, bad, self.tiles)
            with self.assertRaises(ValueError):
                check(path, copies, self.tiles, 52)

    def test_incomplete_or_stale_tile_bank(self):
        for span in (dict(self.span, x=1), dict(self.span, hex='1234'),
                     dict(self.span, hex='1234'*156*12)):
            with self.assertRaises(ValueError):
                cursor_tiles([span])
        self.assertEqual(len(cursor_tiles(json.loads(json.dumps([self.span])))), 13)


if __name__ == '__main__':
    unittest.main()
