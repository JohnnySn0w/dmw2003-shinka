"""Extract local revision guards for the random encounter countdown."""
import argparse
import hashlib
import struct
from pathlib import Path

from generate_menu_hooks import write_changed

FIELD_HASH = '1578efdcfaea58dd52de8c39e61b520f37a7cf7d51e756bd2984283ba54cfc48'


def generate(data):
    if hashlib.sha256(data).hexdigest() != FIELD_HASH:
        raise ValueError('Unsupported FIELDSTG.PRO revision')
    words = struct.unpack('<157I', data[0xf87c:0xfaf0])
    rates = struct.unpack('<6I', data[0x189fc:0x18a14])
    return "/* Generated from the owner's disc. Do not distribute. */\n" + \
        'static const uint32_t encounter_code[] = {\n' + ',\n'.join(
            ','.join(f'0x{x:08x}u' for x in words[i:i+8]) for i in range(0, len(words), 8)) + \
        '\n};\nstatic const uint32_t encounter_costs[] = {' + ','.join(map(str, rates)) + '};\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('field', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    write_changed(args.output, generate(args.field.read_bytes()))
