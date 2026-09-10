"""Read native field trigger regions from a supported 2 MiB RAM snapshot.

Reproduces FIELDSTG's compressed layer lookup without running or modifying game
code. Regions identify condition-table indices, not permission to cross them.
"""
import argparse
import json
from pathlib import Path
import struct


class TriggerMap:
    def __init__(self, ram):
        if len(ram) != 0x200000:
            raise ValueError('Expected a complete 2 MiB RAM snapshot')
        self.ram = ram
        if self.word(0x80092914) != 0x27bdffe8 or self.word(0x80092920) != 0x0c0249ff:
            raise ValueError('Unsupported or absent FIELDSTG lookup')
        self.mode = self.word(0x8004b3f8)
        if not 0x200 <= self.mode < 0x300 or self.word(0x8004b3fc):
            raise ValueError('Expected a stationary field')
        handle = self.word(0x8009b6e0)  # native layer 7
        if not handle:
            raise ValueError('Field has no trigger layer')
        resources = [a for a in range(0x80044b3c, 0x80044f3c, 16)
                     if self.word(a + 4) == handle >> 16]
        if len(resources) != 1 or self.half(resources[0]) != 3:
            raise ValueError('Trigger resource is not uniquely loaded')
        base = self.word(resources[0] + 12)
        packet = base + self.word(base + (handle & 0xffff) * 4)
        self.tables = [packet + self.word(packet + 4 * i) for i in range(6)]
        self.width = self.byte(self.tables[0])
        self.height = self.byte(self.tables[0] + 1)
        if not self.width or not self.height:
            raise ValueError('Empty trigger map')
        self.tables[0] += 2

    def read(self, address, fmt):
        size = struct.calcsize(fmt)
        if not 0x80000000 <= address <= 0x80200000 - size:
            raise ValueError('Layer pointer outside RAM')
        return struct.unpack_from(fmt, self.ram, address - 0x80000000)[0]

    def word(self, a): return self.read(a, '<I')
    def half(self, a): return self.read(a, '<h')
    def byte(self, a): return self.read(a, '<B')

    def at(self, x, y):
        if not 0 <= x < self.width * 128 or not 0 <= y < self.height * 128:
            raise ValueError('Coordinate outside layer')
        t = self.tables
        index = self.byte(t[0] + (y // 128) * self.width + x // 128)
        index = self.byte(t[1] + index * 4 + ((y >> 6) & 1) * 2 + ((x >> 6) & 1))
        for level, shift in ((2, 5), (3, 4), (4, 3)):
            index = self.half(t[level] + 2 * (index * 4 + ((y >> shift) & 1) * 2 + ((x >> shift) & 1)))
            if index < 0:
                raise ValueError('Negative compressed layer index')
        return self.byte(t[5] + index * 64 + (y & 7) * 8 + (x & 7))

    def regions(self, step=4):
        if step not in (1, 2, 4, 8):
            raise ValueError('Sampling step must be 1, 2, 4 or 8')
        found = {}
        for y in range(0, self.height * 128, step):
            for x in range(0, self.width * 128, step):
                value = self.at(x, y)
                # The native gate tests the complete byte before splitting
                # bank/index. Index zero is valid when bank bits are nonzero.
                if not value:
                    continue
                if value not in found:
                    found[value] = dict(value=value, index=value & 31, bank=value >> 5,
                                        sampled_bounds=[x, y, x, y], sample=[x, y], samples=0)
                row = found[value]
                bounds = row['sampled_bounds']
                bounds[:] = [min(bounds[0], x), min(bounds[1], y), max(bounds[2], x), max(bounds[3], y)]
                row['samples'] += 1
        return [found[k] for k in sorted(found)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ram', type=Path)
    parser.add_argument('--step', type=int, choices=(1, 2, 4, 8), default=4)
    args = parser.parse_args()
    try:
        layer = TriggerMap(args.ram.read_bytes())
        print(json.dumps(dict(stage=hex(layer.mode), step=args.step,
                              width=layer.width * 128, height=layer.height * 128,
                              regions=layer.regions(args.step)), indent=2))
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
