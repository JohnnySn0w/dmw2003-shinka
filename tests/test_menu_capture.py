import io
import struct
import unittest

from tools.export_menu_capture import read_frames


def record(frame, width=2, height=1):
    return struct.pack('<8I', frame, width, height, 4096, 7, 1, 0, 65535) + b'\0' * (width * height * 4)


class MenuCaptureTests(unittest.TestCase):
    def test_consecutive_and_blank(self):
        data = b'SHCAP001' + record(12) + record(13, 0, 0) + record(14)
        frames = list(read_frames(io.BytesIO(data)))
        self.assertEqual([item[0]['frame'] for item in frames], [12, 13, 14])
        self.assertEqual(frames[1][1], b'')

    def test_corrupt_or_unfinished_capture(self):
        for data in (b'', b'SHCAP001' + record(12)[:-1],
                     b'SHCAP001' + record(12) + b'\0',
                     b'SHCAP001' + record(12) + record(14),
                     b'SHCAP001' + struct.pack('<8I', 1, 0xffffffff, 240, 0, 0, 0, 0, 0)):
            with self.subTest(data=data[:12]), self.assertRaises(ValueError):
                list(read_frames(io.BytesIO(data)))
