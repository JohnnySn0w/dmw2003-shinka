"""Generate local animation revision guards from the owner's supported disc."""
import argparse
import hashlib
from pathlib import Path
import struct

from build_battle_native import BASE, MODULE_SHA256
from generate_menu_hooks import write_changed


def generate(data):
    if hashlib.sha256(data).hexdigest() != MODULE_SHA256:
        raise ValueError('Unsupported FIGHTSTG.PRO revision')
    # Clip setup, expanded timeline advance, and the model update callback.
    section = data[0x80083a54 - BASE:0x80084464 - BASE]
    words = struct.unpack(f'<{len(section) // 4}I', section)
    return ('/* Generated from the owner\'s disc. Do not distribute. */\n'
            'static const uint32_t battle_motion_code[] = {\n' +
            ',\n'.join(','.join(f'0x{x:08x}u' for x in words[i:i + 8])
                      for i in range(0, len(words), 8)) + '\n};\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    write_changed(args.output, generate(args.module.read_bytes()))
