import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from field_conditions import condition, records, range_predicates, executable_ranges


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

    def test_range_dispatch_and_literal_polarity(self):
        ranges = range_predicates(bytes((7, 0x30, 1, 8, 0x20, 0, 9, 0x31, 0, 255)),
                                  bytes((4, 9, 20, 23)))
        self.assertEqual(ranges, {7: (20, 23), 9: (4, 9)})
        data = struct.pack('<6H3I', 0x7007, 0, 0x7009, 1, 1, 0x200, 0, 0, 0)
        first, second = records(data, 0, 1, ranges)[0]['all_conditions']
        self.assertEqual((first['minimum'], first['maximum'], first['expected_result']), (20, 23, 0))
        self.assertEqual(second['expected_result'], 1)
        self.assertTrue(first['inclusive'])
        self.assertEqual(condition(0x7007, 2, ranges)['expected_result'], 2)
        for flag in (0x7008, 0x7107, 0x7207):
            self.assertEqual(condition(flag, 1, ranges)['meaning'], 'unresolved flag class')
        self.assertEqual(condition(0x7007, 0)['meaning'], 'unresolved flag class')

    def test_invalid_range_tables_and_executable(self):
        for descriptors, ranges in ((b'', b''), (bytes((7,)), b''),
                                    (bytes((7, 0x30, 0)), bytes((20, 23))),
                                    (bytes((7, 0x30, 1, 255)), bytes((20, 23))),
                                    (bytes((7, 0x30, 0, 255)), bytes((23, 20))),
                                    (bytes((7, 0x20, 0, 7, 0x30, 0, 255)), bytes((20, 23)))):
            with self.subTest(descriptors=descriptors), self.assertRaises(ValueError):
                range_predicates(descriptors, ranges)
        with self.assertRaises(ValueError):
            executable_ranges(b'PS-X EXE' + bytes(2048))


if __name__ == '__main__':
    unittest.main()
