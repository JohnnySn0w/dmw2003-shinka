import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from field_conditions import condition, records


class FieldConditionsTests(unittest.TestCase):
    def test_little_endian_pairs_and_stride(self):
        data = b'\x00\x00' + struct.pack('<6H3I', 0x6019, 1, 0x1c51, 0, 8, 0x5fa, 0, 0, 0)
        data += struct.pack('<6H3I', 0x600b, 0, 0xffff, 123, 7, 42, 1, 2, 3)
        first, second = records(data, 2, 2)
        self.assertEqual(first['all_conditions'][0]['operand'], 25)
        self.assertEqual(first['all_conditions'][1]['address'], '0x8004b3bf')
        self.assertEqual(first['all_conditions'][1]['mask'], 2)
        self.assertFalse(first['all_conditions'][1]['expected_set'])
        self.assertEqual(first['event_id'], '0x5fa')
        self.assertEqual(second['offset'], '0x1a')
        self.assertEqual(second['all_conditions'][0]['operator'], '!=')
        self.assertEqual(second['all_conditions'][1]['meaning'], 'unused')
        self.assertNotIn('event_id', second)
        self.assertEqual(second['remaining_words'], ['0x1', '0x2', '0x3'])

    def test_class_storage_and_unknowns(self):
        self.assertEqual(condition(0x4011, 1)['address'], '0x8004b3e0')
        self.assertTrue(condition(0x4011, 2)['expected_set'])
        self.assertEqual(condition(0x1a32, 1)['meaning'], 'unresolved flag class')

    def test_invalid_spans(self):
        for offset, count in ((-2, 1), (1, 1), (0, 0), (0, 257), (2, 1), (0, 2)):
            with self.subTest(offset=offset, count=count), self.assertRaises(ValueError):
                records(bytes(24), offset, count)


if __name__ == '__main__':
    unittest.main()
