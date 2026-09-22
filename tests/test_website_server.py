import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from serve_website import byte_range


class ByteRangeTests(unittest.TestCase):
    def test_explicit_and_open_ranges(self):
        self.assertEqual(byte_range('bytes=0-99', 1000), (0, 99))
        self.assertEqual(byte_range('bytes=500-', 1000), (500, 999))
        self.assertEqual(byte_range('bytes=500-9999', 1000), (500, 999))

    def test_suffix_ranges(self):
        self.assertEqual(byte_range('bytes=-100', 1000), (900, 999))
        self.assertEqual(byte_range('bytes=-2000', 1000), (0, 999))

    def test_invalid_ranges(self):
        for header in ('bytes=-', 'bytes=-0', 'bytes=10-5', 'bytes=1000-',
                       'bytes=0-1,4-5', 'items=0-1', 'bytes=nope'):
            with self.subTest(header=header), self.assertRaises(ValueError):
                byte_range(header, 1000)
        with self.assertRaises(ValueError):
            byte_range('bytes=0-', 0)


if __name__ == '__main__':
    unittest.main()
