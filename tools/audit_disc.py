"""Read-only audit of the supported single-track MODE2/2352 disc dump.

Writes metadata only by default. --extract-exe writes the local boot executable
to the explicitly selected output directory, which must stay out of Git.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def audit(path, output, extract=False, selected=()):
    hashes = {name: hashlib.new(name) for name in ('sha256', 'sha1', 'md5')}
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            for digest in hashes.values():
                digest.update(block)
        size = stream.tell()
        if size % 2352:
            raise ValueError('Input is not a whole number of 2352-byte sectors')

        def read(lba, length):
            if lba < 0 or lba * 2352 + ((length + 2047) // 2048) * 2352 > size:
                raise ValueError('Extent outside disc')
            result = bytearray()
            for sector in range(lba, lba + (length + 2047) // 2048):
                stream.seek(sector * 2352)
                raw = stream.read(2352)
                if raw[:12] != b'\x00' + b'\xff' * 10 + b'\x00' or raw[15] != 2:
                    raise ValueError(f'Not a Mode 2 data sector: {sector}')
                if raw[18] & 0x20:
                    raise ValueError(f'Form 2 sector cannot be read as Form 1: {sector}')
                result.extend(raw[24:2072])
            return bytes(result[:length])

        def directory(lba, length):
            data = read(lba, length)
            entries = []
            offset = 0
            while offset < len(data):
                count = data[offset]
                if not count:
                    offset = (offset // 2048 + 1) * 2048
                    continue
                if count < 34 or offset + count > len(data):
                    raise ValueError('Malformed directory record')
                rec = data[offset:offset + count]
                name = rec[33:33 + rec[32]]
                if name not in (b'\x00', b'\x01'):
                    entries.append(dict(name=name.decode('ascii'), lba=u32(rec, 2),
                                        size=u32(rec, 10), directory=bool(rec[25] & 2)))
                offset += count
            return entries

        pvd = read(16, 2048)
        if pvd[:7] != b'\x01CD001\x01':
            raise ValueError('Missing ISO9660 primary volume descriptor')
        root = directory(u32(pvd, 158), u32(pvd, 166))
        table = read(u32(pvd, 140), u32(pvd, 132))
        paths = []
        offset = 0
        while offset < len(table):
            n = table[offset]
            if not n or offset + 8 + n > len(table):
                raise ValueError('Malformed path table')
            name = table[offset + 8:offset + 8 + n]
            paths.append(dict(name='/' if name == b'\x00' else name.decode('ascii'),
                              lba=u32(table, offset + 2),
                              parent=struct.unpack_from('<H', table, offset + 6)[0]))
            offset += 8 + n + (n % 2)
        boot = next(e for e in root if e['name'] == 'SLES_039.36;1')
        exe = read(boot['lba'], boot['size'])
        if exe[:8] != b'PS-X EXE':
            raise ValueError('Boot file lacks PS-X EXE header')
        sha1 = hashes['sha1'].hexdigest()
        report = dict(format='MODE2/2352', size=size,
                      hashes={n: h.hexdigest() for n, h in hashes.items()},
                      matches_recomp_known_sha1=sha1 == '457cb233349ba841e03b33d8060f8fbcadd45cb3',
                      volume=pvd[40:72].decode('ascii').strip(), root=root, path_table=paths,
                      executable=dict(sha256=hashlib.sha256(exe).hexdigest(),
                                      entry_pc=hex(u32(exe, 16)), load_address=hex(u32(exe, 24)),
                                      text_size=hex(u32(exe, 28)), stack_base=hex(u32(exe, 48))))
        # Enumerate directories named in the path table, even if hidden at root.
        catalog = []
        for entry in paths:
            first_sector = read(entry['lba'], 2048)
            length = u32(first_sector, 10)
            catalog.append(dict(path=entry, entries=directory(entry['lba'], length)))
        report['catalog'] = catalog
        selected_data = {}
        for name in selected:
            if Path(name).name != name or '/' in name or '\\' in name or ':' in name:
                raise ValueError('Extraction accepts a basename only')
            matches = [e for c in catalog for e in c['entries']
                       if not e['directory'] and e['name'].split(';')[0] == name]
            if len(matches) != 1:
                raise ValueError(f'Expected one match for {name}, found {len(matches)}')
            entry = matches[0]
            selected_data[name] = read(entry['lba'], entry['size'])
        report['selected_files'] = {name: dict(size=len(data), sha256=hashlib.sha256(data).hexdigest())
                                    for name, data in selected_data.items()}
        output.mkdir(parents=True, exist_ok=True)
        (output / 'disc-audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        if extract:
            (output / 'SLES_039.36').write_bytes(exe)
        for name, data in selected_data.items():
            (output / name).write_bytes(data)
        print(json.dumps({k: v for k, v in report.items() if k not in ('catalog', 'path_table')}, indent=2))
        print(f'Path-table directories: {len(paths)}; file records: {sum(len(c["entries"]) for c in catalog)}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bin', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--extract-exe', action='store_true')
    parser.add_argument('--extract-file', action='append', default=[], help='Unique ISO basename, e.g. STSTATUS.PRO')
    args = parser.parse_args()
    audit(args.bin, args.output, args.extract_exe, args.extract_file)
