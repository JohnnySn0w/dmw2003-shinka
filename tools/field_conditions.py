"""Read explicitly located FIELDSTG condition/action records from owned modules.

This does not discover records or interpret the event bytecode. Offsets must
come from a separately traced field table, not a search for plausible values.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct


PAL_EXE_SHA256 = '15f37849a81b9f00e7f20d00de7a465b663a9e86b9d08b05d32dd386be95c546'


def range_predicates(descriptors, ranges):
    """Decode only class-0x70 descriptors routed to the native range reader."""
    found = {}
    seen = set()
    for offset in range(0, len(descriptors), 3):
        index = descriptors[offset]
        if index == 0xff:
            return found
        if offset + 3 > len(descriptors) or index in seen:
            raise ValueError('Malformed predicate descriptors')
        seen.add(index)
        kind, argument = descriptors[offset + 1:offset + 3]
        if kind & 0xf0 != 0x30:
            continue
        position = argument * 2
        if position + 2 > len(ranges):
            raise ValueError('Story range extends past table')
        low, high = ranges[position:position + 2]
        if low > high:
            raise ValueError('Reversed story range')
        found[index] = (low, high)
    raise ValueError('Unterminated predicate descriptors')


def executable_ranges(data):
    # Whole-file identity guards the dispatch code and both table boundaries.
    # No executable bytes or predicate tables are redistributed with this tool.
    if hashlib.sha256(data).hexdigest() != PAL_EXE_SHA256:
        raise ValueError('Unsupported executable; expected original PAL SLES_039.36')
    base = struct.unpack_from('<I', data, 24)[0]
    def span(start, end):
        return data[start - base + 2048:end - base + 2048]
    return range_predicates(span(0x80048ad8, 0x80048c44), span(0x80048cb4, 0x80048cf6))


def condition(flag, value, story_ranges=None):
    result = {'flag': hex(flag), 'value': value}
    if flag == 0xffff:
        result['meaning'] = 'unused'
        return result
    group = (flag >> 8) & 0xfe
    index = flag & 0x1ff
    if group == 0x60:
        result.update(kind='story', operator='==' if value else '!=', operand=index)
    elif group == 0x70 and story_ranges is not None and index in story_ranges:
        low, high = story_ranges[index]
        # Class 0x70 compares the Boolean reader result with the literal value.
        result.update(kind='story_range', minimum=low, maximum=high,
                      inclusive=True, expected_result=value)
    elif group in (0x1c, 0x40):
        base = {0x1c: 0x8004b3b5, 0x40: 0x8004b3de}[group]
        result.update(kind='bit', address=hex(base + index // 8),
                      mask=1 << (index % 8), expected_set=bool(value))
    else:
        result['meaning'] = 'unresolved flag class'
    return result


def records(data, offset, count, story_ranges=None):
    if offset < 0 or offset % 2 or count < 1 or count > 256:
        raise ValueError('Use an even nonnegative offset and count 1..256')
    if offset + count * 24 > len(data):
        raise ValueError('Requested records extend past the module')
    out = []
    for position in range(offset, offset + count * 24, 24):
        first, a, second, b, action, argument = struct.unpack_from('<6H', data, position)
        record = {'offset': hex(position), 'all_conditions': [condition(first, a, story_ranges), condition(second, b, story_ranges)],
                  'action': action, 'argument': hex(argument)}
        if action == 8:
            record['event_id'] = hex(argument)
        # Remaining bytes are type-dependent; preserve them without guessing
        # trigger geometry, NPC identity, or scene completion behavior.
        record['remaining_words'] = [hex(v) for v in struct.unpack_from('<3I', data, position + 12)]
        out.append(record)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module', type=Path)
    parser.add_argument('--offset', type=lambda v: int(v, 0), required=True)
    parser.add_argument('--count', type=int, default=1)
    parser.add_argument('--exe', type=Path, help='Owned original PAL executable, to resolve story-range predicates')
    args = parser.parse_args()
    try:
        data = args.module.read_bytes()
        story_ranges = executable_ranges(args.exe.read_bytes()) if args.exe else None
        result = records(data, args.offset, args.count, story_ranges)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({'module': args.module.name, 'sha256': hashlib.sha256(data).hexdigest(),
                      'executable_sha256': PAL_EXE_SHA256 if args.exe else None,
                      'records': result}, indent=2))


if __name__ == '__main__':
    main()
