"""Generate private revision guards for the original map and Status controller."""
import argparse
import hashlib
import struct
from pathlib import Path
from generate_menu_hooks import write_changed

STATUS_HASH = '892300687ec6a8d69c7c2b6c6111adffb5df3beee301e9ef919ee78c02f24e8a'
RANGES = ((0x80098294, 0x80098450), (0x80098b84, 0x80099384),
          (0x800996ec, 0x80099b60), (0x8009a670, 0x8009a784))


def generate(data):
    if hashlib.sha256(data).hexdigest() != STATUS_HASH:
        raise ValueError('Unsupported STSTATUS.PRO revision')
    output = "/* Generated from the owner's disc. Do not distribute. */\n"
    for i, (start, end) in enumerate(RANGES):
        words = struct.unpack(f'<{(end-start)//4}I', data[start-0x80082cb0:end-0x80082cb0])
        output += f'static const uint32_t map_guard_{i}[] = {{\n' + ',\n'.join(
            ','.join(f'0x{w:08x}u' for w in words[n:n+8]) for n in range(0,len(words),8)) + '\n};\n'
    output += 'static const struct { uint32_t address, count; const uint32_t* words; } map_guards[] = {\n'
    output += ',\n'.join(f'{{0x{s:08x}u, {(e-s)//4}, map_guard_{i}'+'}' for i,(s,e) in enumerate(RANGES))+'\n};\n'
    mapping = data[0x8009b5fc-0x80082cb0:0x8009b5fc-0x80082cb0+215]
    return output+'static const uint8_t map_stage_icons[] = {'+','.join(map(str,mapping))+'};\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('status',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    write_changed(args.output,generate(args.status.read_bytes()))
