"""Generate local chart metadata from the owner's verified disc files."""
import argparse
import hashlib
import struct
from pathlib import Path

from evolution_hints import read_requirements
from generate_menu_hooks import write_changed

LAB_HASH = '3dec8fc81a7db98010b8f10cc9bd9cc06f5b09216885f6f9ce1e79e088d6de59'
EXE_HASH = '15f37849a81b9f00e7f20d00de7a465b663a9e86b9d08b05d32dd386be95c546'


def generate(reward, lab, exe):
    requirements = read_requirements(reward)
    if hashlib.sha256(lab).hexdigest() != LAB_HASH or hashlib.sha256(exe).hexdigest() != EXE_HASH:
        raise ValueError('Unsupported lab or executable revision')
    profile = 0x8003ef5c - 0x80010000 + 0x800
    ids = [struct.unpack_from('<H', exe, profile + i * 88)[0] for i in range(52)]
    name_ids = [exe[profile + i * 88 + 0x55] for i in range(52)]
    lines = ["/* Generated from the owner's disc. Do not distribute. */",
             'static const uint16_t evolution_ids[52] = {' + ','.join(map(str, ids)) + '};',
             'static const uint8_t evolution_name_ids[52] = {' + ','.join(map(str, name_ids)) + '};',
             'static const uint16_t evolution_layout[8][16][5] = {']
    for rookie in range(8):
        rows = []
        for row in range(16):
            offset = 0x8008f768 - 0x80082cb0 + rookie * 192 + row * 12
            count, *forms = struct.unpack_from('<6H', lab, offset)
            if count != sum(bool(x) for x in forms) or any(x and x not in ids for x in forms):
                raise ValueError('Unknown chart layout')
            rows.append('{' + ','.join(map(str, forms)) + '}')
        lines.append('{' + ','.join(rows) + '},')
    lines += ['};', 'static const uint8_t evolution_requirements[8][44][3] = {']
    for entries in requirements.values():
        rows = []
        for i, entry in enumerate(entries):
            if entry.destination != i + 9 or any(not 1 <= f <= 52 for f, _ in entry.forms):
                raise ValueError('Unknown requirement-to-profile mapping')
            forms = [f for f, _ in entry.forms] + [0, 0]
            rows.append('{' + ','.join(map(str, [*forms[:2], entry.extra_type])) + '}')
        lines.append('{' + ','.join(rows) + '},')
    return '\n'.join([*lines, '};', ''])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    write_changed(args.output, generate(*(args.directory.joinpath(name).read_bytes()
                  for name in ('STFGTREP.PRO', 'STGDGLAB.PRO', 'SLES_039.36'))))
