import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from inspect_runtime_objects import (MAX_CHILDREN, MODE_ADDRESS, OWNER_ADDRESS,
                                     RAM_SIZE, SIGNATURE, capture_ram,
                                     inspect_objects, ram_offset)


class RuntimeObjectTests(unittest.TestCase):
    def setUp(self):
        self.ram = bytearray(RAM_SIZE)
        struct.pack_into('<I', self.ram, MODE_ADDRESS, 0x600)

    def object(self, offset, children=(), table=None):
        self.ram[offset + 0x28:offset + 0x48] = SIGNATURE
        struct.pack_into('<I', self.ram, offset + 0x48, 0x80083e0c)
        struct.pack_into('<4I', self.ram, offset + 0xc, 1, 2, 3, 4)
        table = table if table is not None else offset + 0x100
        struct.pack_into('<2I', self.ram, offset + 0x20, len(children), 0x80000000 + table)
        if children:
            struct.pack_into(f'<{len(children)}I', self.ram, table, *children)

    def owner(self, address):
        struct.pack_into('<I', self.ram, OWNER_ADDRESS, address)

    def test_live_tree_distinguishes_detached_signature(self):
        self.object(0x90000, (0, 0xa0091000))
        self.object(0x91000)
        self.object(0x92000)
        self.owner(0x80090000)
        result = inspect_objects(self.ram)
        self.assertEqual((result['candidate_count'], result['reachable_count']), (3, 2))
        self.assertEqual(result['objects'][0]['children'][0]['slot'], 1)
        self.assertEqual(result['objects'][1]['parents'], ['0x80090000'])
        self.assertFalse(result['objects'][2]['reachable'])

    def test_cycles_and_duplicate_edges_terminate(self):
        self.object(0x90000, (0x80091000, 0x80091000))
        self.object(0x91000, (0x80090000,))
        self.owner(0xa0090000)
        result = inspect_objects(self.ram)
        self.assertEqual(result['reachable_count'], 2)
        self.assertTrue(result['owner_found'])

    def test_dangling_and_invalid_pointers_are_not_followed(self):
        self.object(0x90000, (0x80091000, 0xbf801810, 0x80091001))
        self.owner(0x80090000)
        obj = inspect_objects(self.ram)['objects'][0]
        self.assertEqual([child['recognized'] for child in obj['children']], [False] * 3)
        self.assertEqual([child['address'] for child in obj['children']], ['0x80091000', None, None])

    def test_child_table_cannot_wrap_or_read_mmio(self):
        self.object(0x90000)
        for pointer in (0, 0x801ffffc, 0xbf801810, 0x80090001):
            struct.pack_into('<2I', self.ram, 0x90020, 2, pointer)
            obj = inspect_objects(self.ram)['objects'][0]
            self.assertEqual(obj['children'], [])
            self.assertTrue(obj['warnings'])

    def test_excess_child_count_is_reported_without_following(self):
        self.object(0x90000)
        struct.pack_into('<I', self.ram, 0x90020, MAX_CHILDREN + 1)
        obj = inspect_objects(self.ram)['objects'][0]
        self.assertEqual(obj['children'], [])
        self.assertIn('inspection limit', obj['warnings'][0])

    def test_incomplete_unaligned_and_noncode_headers_are_rejected(self):
        self.ram[:len(SIGNATURE)] = SIGNATURE
        self.object(0x90001)
        self.object(0x91000)
        struct.pack_into('<I', self.ram, 0x91048, 0xbf801810)
        self.ram[-len(SIGNATURE):] = SIGNATURE
        self.assertEqual(inspect_objects(self.ram)['candidate_count'], 0)

    def test_wrong_size_is_rejected_and_missing_owner_is_explicit(self):
        with self.assertRaises(ValueError):
            inspect_objects(bytes(64))
        self.object(0x90000)
        result = inspect_objects(self.ram)
        self.assertFalse(result['owner_found'])
        self.assertEqual(result['reachable_count'], 0)

    def test_ram_aliases_and_bounds(self):
        for value in (0x10000, 0x80010000, 0xa0010000):
            self.assertEqual(ram_offset(value), 0x10000)
        self.assertEqual(ram_offset(0x801ffffc), RAM_SIZE - 4)
        for value in (-1, 0x100000000, 0x1f801810, 0xc0010000, 0x80200000, 0x80010001):
            self.assertIsNone(ram_offset(value))

    def test_capture_uses_one_read_only_command(self):
        calls = []

        def transport(command, port):
            calls.append((command, port))
            return dict(ok=True, len=RAM_SIZE, hex=self.ram.hex())

        self.assertEqual(capture_ram(4383, transport), self.ram)
        self.assertEqual(calls, [(dict(cmd='read_ram', addr='0x80000000', len=RAM_SIZE), 4383)])

    def test_capture_rejects_error_or_truncation(self):
        with self.assertRaises(RuntimeError):
            capture_ram(4383, lambda *_: dict(ok=False, err='Unavailable'))
        with self.assertRaises(ValueError):
            capture_ram(4383, lambda *_: dict(ok=True, len=RAM_SIZE, hex='00'))


if __name__ == '__main__':
    unittest.main()
