"""Resolve sampled Windows caller stacks using the matching local MSVC map.

Percentages are wall-time sample residency, NOT inclusive CPU percentages.
Optimized/inlined frames may be absent; system DLLs remain module+offset labels.
"""
import argparse
from bisect import bisect_right
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct


def pe_timestamp(path):
    with path.open('rb') as stream:
        if stream.read(2) != b'MZ':
            raise ValueError('Not a PE executable')
        stream.seek(0x3c)
        offset = struct.unpack('<I', stream.read(4))[0]
        stream.seek(offset)
        if stream.read(4) != b'PE\0\0':
            raise ValueError('Missing PE signature')
        stream.read(4)
        return struct.unpack('<I', stream.read(4))[0]


def map_symbols(text, base):
    preferred = re.search(r'Preferred load address is\s+([0-9a-fA-F]+)', text)
    if not preferred:
        raise ValueError('Map has no preferred load address')
    slide = base - int(preferred[1], 16)
    symbols = []
    for line in text.splitlines():
        match = re.match(r'\s+[0-9a-fA-F]{4}:[0-9a-fA-F]+\s+(\S+)\s+([0-9a-fA-F]{16})\s+f\s+(.*)', line)
        if match:
            symbols.append((int(match[2], 16) + slide, match[1], match[3].strip()))
    if not symbols:
        raise ValueError('Map has no function symbols')
    # Folded functions may share an address; retain aliases instead of choosing
    # an arbitrary implementation name and claiming its cost.
    grouped = {}
    for address, name, obj in sorted(symbols):
        grouped.setdefault(address, []).append((name, obj))
    return [(address, '|'.join(sorted({name for name, _ in entries})),
             '|'.join(sorted({obj for _, obj in entries})))
            for address, entries in sorted(grouped.items())]


def summarize(record, symbols, game):
    addresses = [item[0] for item in symbols]

    def resolve(address):
        for module in record['modules']:
            if module['base'] <= address < module['base'] + module['size']:
                if module == game:
                    index = bisect_right(addresses, address) - 1
                    if index >= 0 and address - addresses[index] < 65536:
                        return symbols[index][1]
                return f"{module['path'].replace(chr(92), '/').rsplit('/', 1)[-1]}+0x{address-module['base']:x}"
        return f'unknown+0x{address:x}'

    leaves, inclusive, edges, stacks, depths = (Counter() for _ in range(5))
    stopped = []
    for sample in record['samples']:
        if not sample['pcs']:
            raise ValueError('Empty stack sample')
        # Return PCs point just past the call; resolve their preceding byte.
        labels = [resolve(pc if i == 0 else pc - 1) for i, pc in enumerate(sample['pcs'])]
        leaves[labels[0]] += 1
        inclusive.update(set(labels))
        edges.update(set(f'{caller} -> {callee}' for callee, caller in zip(labels, labels[1:])))
        stacks[';'.join(reversed(labels))] += 1
        depths[len(labels)] += 1
        stopped.append(sample['stop_us'])
    count = sum(leaves.values())
    if not count:
        raise ValueError('No samples')

    def rows(counter, limit=60):
        return [dict(name=name, samples=value, sample_percent=100*value/count)
                for name, value in counter.most_common(limit)]

    stopped.sort()
    return dict(schema=1, samples=count, wall_seconds=record['wall_seconds'],
                thread_cpu_seconds=record['thread_cpu_seconds'],
                leaf=rows(leaves), inclusive=rows(inclusive), caller_edges=rows(edges),
                stack_depths=dict(sorted(depths.items())),
                depth_limit_samples=sum(bool(s['truncated']) for s in record['samples']),
                single_frame_samples=depths[1],
                snapshot_us=dict(median=stopped[len(stopped)//2],
                                 p95=stopped[min(len(stopped)-1, int(len(stopped)*.95))],
                                 maximum=max(stopped), total=sum(stopped)),
                folded=stacks,
                caveats=['Wall-time sample residency is not CPU-time attribution; waits are included.',
                         'Use separate unsampled runs to establish speed or CPU savings.',
                         'MSVC map labels are nearest preceding functions (within 64 KiB), not source lines.',
                         'Inlining/tail calls hide frames; identical-code folding retains name aliases.',
                         'System DLLs are module+offset only; no symbol server is contacted.',
                         'Only the chosen thread is sampled; this is not a whole-process profile.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--map', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    record = json.loads(args.input.read_text())
    game = next(m for m in record['modules'] if m['path'].lower().endswith('dmw2003-shinka.exe'))
    text = args.map.read_text(errors='replace')
    stamp = re.search(r'Timestamp is\s+([0-9a-fA-F]+)', text)
    timestamp = game['timestamp'] if 'timestamp' in game else pe_timestamp(Path(game['path']))
    if not stamp or int(stamp[1], 16) != timestamp:
        raise ValueError('Map timestamp does not match the sampled executable')
    result = summarize(record, map_symbols(text, game['base']), game)
    result['map_sha256'] = hashlib.sha256(args.map.read_bytes()).hexdigest()
    result['input'] = str(args.input.resolve())
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ('samples', 'stack_depths', 'snapshot_us', 'inclusive', 'leaf')}, indent=2))


if __name__ == '__main__':
    main()
