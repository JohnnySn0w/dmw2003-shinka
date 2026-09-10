import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from field_triggers import TriggerMap


def snapshot():
    ram = bytearray(0x200000)
    def put(a, value): struct.pack_into('<I', ram, a - 0x80000000, value)
    put(0x80092914, 0x27bdffe8); put(0x80092920, 0x0c0249ff)
    put(0x8004b3f8, 0x23e); put(0x8009b6e0, 0x40e0002)
    put(0x80044b3c, 3); put(0x80044b40, 0x40e); put(0x80044b48, 0x80060000)
    put(0x80060008, 0x100)
    tables = (0x80060200, 0x80060300, 0x80060400, 0x80060600, 0x80060800, 0x80061000)
    for i, table in enumerate(tables): put(0x80060100 + 4*i, table - 0x80060100)
    ram[0x60200:0x60204] = bytes((2, 1, 0, 1))
    ram[0x60300:0x60308] = bytes(range(8))
    for address, count in ((0x60400, 32), (0x60600, 128), (0x60800, 512)):
        for i in range(count): struct.pack_into('<h', ram, address+2*i, i)
    for y in range(128):
        for x in range(256):
            tile = (x // 128) * 256
            for bit in range(3, 7):
                tile |= (((y >> bit) & 1)*2 + ((x >> bit) & 1)) << (2*(bit-3))
            ram[0x61000 + tile*64 + (y % 8)*8 + x % 8] = (x + 3*y) % 256
    return ram


class TriggerMapTests(unittest.TestCase):
    def test_every_compression_level_and_pixel(self):
        layer = TriggerMap(snapshot())
        for y in range(128):
            for x in range(256):
                self.assertEqual(layer.at(x, y), (x + 3*y) % 256)

    def test_samples_are_inside_their_reported_trigger(self):
        layer = TriggerMap(snapshot())
        regions = layer.regions()
        self.assertIn(32, [row['value'] for row in regions])
        self.assertNotIn(0, [row['value'] for row in regions])
        for row in regions:
            self.assertEqual(layer.at(*row['sample']), row['value'])
            self.assertEqual(row['index'], row['value'] & 31)
            self.assertGreater(row['samples'], 0)
        for xy in ((-1, 0), (256, 0), (0, 128)):
            with self.assertRaises(ValueError): layer.at(*xy)

    def test_rejects_partial_unknown_and_unloaded_snapshots(self):
        with self.assertRaises(ValueError): TriggerMap(bytes(32))
        for offset in (0x92914, 0x44b3c, 0x9b6e0):
            ram = snapshot(); ram[offset:offset+4] = bytes(4)
            with self.assertRaises(ValueError): TriggerMap(ram)
        ram = snapshot(); struct.pack_into('<I', ram, 0x44b48, 0xffffffff)
        with self.assertRaises(ValueError): TriggerMap(ram)


if __name__ == '__main__': unittest.main()
