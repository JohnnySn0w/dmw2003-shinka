"""Tag an existing local music pack's instrument roles without re-rendering audio."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def upgrade(data, report):
    if hashlib.sha256(data).hexdigest() != report.get('sha256'):
        raise ValueError('Music pack does not match its routing report')
    if data[:8] != b'SHKMUS01':
        raise ValueError('Expected a legacy SHKMUS01 pack')
    position = 8
    def take(size):
        nonlocal position
        if size < 0 or position + size > len(data):
            raise ValueError('Truncated music pack')
        result = data[position:position+size]
        position += size
        return result
    def word():
        return struct.unpack('<I', take(4))[0]
    rate, count = word(), word()
    if rate != 44100 or not 1 <= count <= 64 or len(report['banks']) != count:
        raise ValueError('Invalid bank count or sample rate')
    output = bytearray(b'SHKMUS02' + struct.pack('<II', rate, count))
    counts = dict(melody=0, bass=0, percussion=0)
    total = 0
    for bank in report['banks']:
        size, samples = word(), word()
        if not 16 <= size <= 524288 or not 1 <= samples <= 256 or len(bank['samples']) != samples:
            raise ValueError('Bank does not match its routing report')
        output.extend(struct.pack('<II', size, samples))
        output.extend(take(size))
        for route in bank['samples']:
            offset = word()
            if offset % 16 or offset > size - 16:
                raise ValueError('Invalid sample offset')
            instrument = route['soundfont']
            if not isinstance(instrument, str) or not instrument:
                raise ValueError('Missing instrument route')
            role = 2 if instrument == 'drums' else 1 if instrument == 'bass' else 0
            counts[('melody', 'bass', 'percussion')[role]] += 1
            output.extend(struct.pack('<II', offset, role))
            for _ in range(3):
                frames, loop = word(), word()
                if not 1 <= frames <= 132300 or (loop != 0xffffffff and loop >= frames):
                    raise ValueError('Invalid replacement wave')
                total += frames * 2
                if total > 256 * 1024 * 1024:
                    raise ValueError('Music pack exceeds memory budget')
                output.extend(struct.pack('<II', frames, loop))
                output.extend(take(frames * 2))
    if position != len(data):
        raise ValueError('Trailing music data')
    return bytes(output), counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pack', type=Path)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new output directory')
    report = json.loads(args.report.read_text(encoding='utf-8'))
    data, counts = upgrade(args.pack.read_bytes(), report)
    report['source_pack_sha256'] = report['sha256']
    report['sha256'] = hashlib.sha256(data).hexdigest()
    report['pack_format'] = 'SHKMUS02'
    report['instrument_roles'] = counts
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'music-live.bin').write_bytes(data)
    (args.output / 'music-live.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(bytes=len(data), instrument_roles=counts)))


if __name__ == '__main__':
    main()
