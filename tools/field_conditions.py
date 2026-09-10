"""Read explicitly located FIELDSTG condition/action records from owned modules.

This does not discover records or interpret the event bytecode. Offsets must
come from a separately traced field table, not a search for plausible values.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def condition(flag, value):
    result = {'flag': hex(flag), 'value': value}
    if flag == 0xffff:
        result['meaning'] = 'unused'
        return result
    group = (flag >> 8) & 0xfe
    index = flag & 0x1ff
    if group == 0x60:
        result.update(kind='story', operator='==' if value else '!=', operand=index)
    elif group in (0x1c, 0x40):
        base = {0x1c: 0x8004b3b5, 0x40: 0x8004b3de}[group]
        result.update(kind='bit', address=hex(base + index // 8),
                      mask=1 << (index % 8), expected_set=bool(value))
    else:
        result['meaning'] = 'unresolved flag class'
    return result


def records(data, offset, count):
    if offset < 0 or offset % 2 or count < 1 or count > 256:
        raise ValueError('Use an even nonnegative offset and count 1..256')
    if offset + count * 24 > len(data):
        raise ValueError('Requested records extend past the module')
    out = []
    for position in range(offset, offset + count * 24, 24):
        first, a, second, b, action, argument = struct.unpack_from('<6H', data, position)
        record = {'offset': hex(position), 'all_conditions': [condition(first, a), condition(second, b)],
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
    args = parser.parse_args()
    try:
        data = args.module.read_bytes()
        result = records(data, args.offset, args.count)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({'module': args.module.name, 'sha256': hashlib.sha256(data).hexdigest(),
                      'records': result}, indent=2))


if __name__ == '__main__':
    main()
