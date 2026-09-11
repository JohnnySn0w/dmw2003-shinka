"""Map supported DM2003 controller headers from one read-only RAM snapshot.

Capture from a copied-save diagnostic instance, or analyze a local 2 MiB dump.
Signature matches are candidates: detached headers can survive object deletion.
This tool never changes game state or enables a recorder in the runner.
"""
import argparse
from collections import deque
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct

from runtime_probe import request

RAM_SIZE = 0x200000
MODE_ADDRESS = 0x4b3f8
OWNER_ADDRESS = 0x5ccbc
MAX_CHILDREN = 256
HEADER_SIZE = 0x50
SETTERS = (0x80014274, 0x80014288, 0x80014298, 0x800142a4,
           0x800142ac, 0x800142c8, 0x800142e0, 0x800142f4)
SIGNATURE = struct.pack('<8I', *SETTERS)


def ram_offset(address, length=4):
    """Accept physical RAM and its KSEG0/KSEG1 aliases; reject MMIO and wrap."""
    if not isinstance(address, int) or not 0 <= address <= 0xffffffff:
        return None
    if address & 0xe0000000 not in (0, 0x80000000, 0xa0000000):
        return None
    offset = address & 0x1fffffff
    if address & 3 or length < 0 or offset > RAM_SIZE - length:
        return None
    return offset


def canonical(address):
    offset = ram_offset(address)
    return f'0x{0x80000000 + offset:08X}' if offset is not None else None


def inspect_objects(ram):
    if len(ram) != RAM_SIZE:
        raise ValueError('Expected exactly 2 MiB of PSX main RAM')
    objects = {}
    position = 0
    while True:
        match = ram.find(SIGNATURE, position)
        if match < 0:
            break
        position = match + 1
        start = match - 0x28
        if start < 0 or start & 3 or start + HEADER_SIZE > RAM_SIZE:
            continue
        words = struct.unpack_from('<20I', ram, start)
        callback = words[18]
        code = ram_offset(callback)
        if code is None or code < 0x10000:
            continue
        address = canonical(start)
        count, table = words[8:10]
        warnings, children = [], []
        if count > MAX_CHILDREN:
            warnings.append(f'Child count {count} exceeds inspection limit {MAX_CHILDREN}')
        elif count:
            table_offset = ram_offset(table, count * 4)
            if not table or table_offset is None:
                warnings.append('Child table is outside aligned main RAM')
            else:
                for slot, child in enumerate(struct.unpack_from(f'<{count}I', ram, table_offset)):
                    if child:
                        children.append(dict(slot=slot, raw=f'0x{child:08X}', address=canonical(child)))
        objects[address] = dict(address=address, callback=f'0x{callback:08X}',
                                state=list(words[3:7]), child_count=count,
                                child_table=f'0x{table:08X}', children=children,
                                reachable=False, parents=[], warnings=warnings)
    for obj in objects.values():
        for child in obj['children']:
            child['recognized'] = child['address'] in objects
            if child['recognized']:
                objects[child['address']]['parents'].append(obj['address'])
    owner = struct.unpack_from('<I', ram, OWNER_ADDRESS)[0]
    owner_key = canonical(owner) if owner else None
    pending = deque([owner_key] if owner_key in objects else [])
    visited = set()
    while pending:
        address = pending.popleft()
        if address in visited:
            continue
        visited.add(address)
        obj = objects[address]
        obj['reachable'] = True
        pending.extend(child['address'] for child in obj['children'] if child['recognized'])
    return dict(schema=1, ram_sha256=hashlib.sha256(ram).hexdigest(),
                mode=struct.unpack_from('<I', ram, MODE_ADDRESS)[0],
                mode_owner=f'0x{owner:08X}', owner_found=owner_key in objects,
                candidate_count=len(objects), reachable_count=len(visited),
                objects=list(objects.values()),
                caveats=['Signature matches are candidates, not an allocation/liveness oracle.',
                         'Reachability follows recognized child tables from the current mode owner.',
                         'Detached candidates may be stale, pooled, or independently owned.',
                         'Callbacks identify code addresses, not verified semantic roles.'])


def capture_ram(port, transport=request):
    reply = transport(dict(cmd='read_ram', addr='0x80000000', len=RAM_SIZE), port)
    if reply.get('ok') is not True:
        raise RuntimeError(reply.get('err') or reply.get('error') or 'RAM read failed')
    ram = bytes.fromhex(reply['hex'])
    if reply.get('len') != RAM_SIZE or len(ram) != RAM_SIZE:
        raise ValueError('Incomplete RAM snapshot')
    return ram


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--ram', type=Path, help='Existing raw 2 MiB RAM snapshot')
    source.add_argument('--port', type=int, help='Copied-save runner debug port')
    parser.add_argument('--expect-mode', type=lambda value: int(value, 0))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--save-ram', type=Path, help='Also retain the live capture locally')
    args = parser.parse_args()
    if args.save_ram and args.port is None:
        parser.error('--save-ram requires --port')
    destinations = [path.resolve() for path in (args.output, args.save_ram) if path]
    if len(destinations) != len(set(destinations)) or any(path.exists() for path in destinations):
        parser.error('Output paths must be distinct and must not already exist')
    ram = args.ram.read_bytes() if args.ram else capture_ram(args.port)
    result = inspect_objects(ram)
    if args.expect_mode is not None and result['mode'] != args.expect_mode:
        parser.error(f"Captured mode {result['mode']:#x}, expected {args.expect_mode:#x}")
    result['inspected_at'] = datetime.now(timezone.utc).isoformat()
    result['source'] = str(args.ram) if args.ram else dict(debug_port=args.port)
    for path in destinations:
        path.parent.mkdir(parents=True, exist_ok=True)
    if args.save_ram:
        with args.save_ram.open('xb') as handle:
            handle.write(ram)
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print(f"Mode {result['mode']:#x}: {result['candidate_count']} candidates, "
          f"{result['reachable_count']} reachable from the mode owner")


if __name__ == '__main__':
    main()
