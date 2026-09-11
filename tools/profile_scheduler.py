"""Read scheduler counters from a Windows test process without suspending it.

Requires the matching executable's MSVC /MAP file and its ASLR module base.
Use a copied save profile. --slot explicitly loads a checkpoint; otherwise
the current scene is observed. No process memory is written.
"""
import argparse
import ctypes
from ctypes import wintypes as w
import hashlib
import json
from pathlib import Path
import re
import struct
import time

from dev_nav import Navigator
from profile_runtime import ProcessClock

COUNTERS = ('psx_cycle_count', 's_frame_count', 'g_spu_sample_deadline_queries',
            'g_spu_sample_service_checks', 'g_guest_store_count', 'g_mmio_access_count',
            'shinka_cd_deadline_queries', 'shinka_cd_latched_queries')


def validate_loaded_image(map_text, base, read_bytes, allow_relocated_header=True):
    """Check the live PE identity before interpreting map offsets as counters."""
    stamp = re.search(r'Timestamp is\s+([0-9a-fA-F]+)', map_text)
    preferred = re.search(r'Preferred load address is\s+([0-9a-fA-F]+)', map_text)
    if not stamp or not preferred:
        raise ValueError('Map is missing its image identity')
    dos = read_bytes(base, 64)
    if len(dos) != 64 or dos[:2] != b'MZ':
        raise ValueError('Module base does not point to a PE image')
    offset = struct.unpack_from('<I', dos, 60)[0]
    if not 64 <= offset <= 0x100000:
        raise ValueError('Invalid PE header offset')
    nt = read_bytes(base + offset, 84)
    if len(nt) != 84 or nt[:4] != b'PE\0\0' or struct.unpack_from('<H', nt, 4)[0] != 0x8664:
        raise ValueError('Target must be an AMD64 PE executable')
    if struct.unpack_from('<H', nt, 24)[0] != 0x20b:
        raise ValueError('Target must use PE32+ headers')
    timestamp = struct.unpack_from('<I', nt, 8)[0]
    image_base = struct.unpack_from('<Q', nt, 48)[0]
    image_size = struct.unpack_from('<I', nt, 80)[0]
    preferred_base = int(preferred[1], 16)
    # Windows may rewrite the mapped ImageBase to its ASLR address. Validate
    # the original preferred address against the on-disk header separately.
    base_matches = image_base == preferred_base or (allow_relocated_header and image_base == base)
    if timestamp != int(stamp[1], 16) or not base_matches:
        raise ValueError(f'Map does not match the loaded executable: timestamp {timestamp:08x} '
                         f'(map {stamp[1]}), header base {image_base:#x} (map {preferred[1]}). '
                         'Aborting before save load or measurement')
    if image_size < offset + len(nt):
        raise ValueError('Invalid loaded image size')
    return dict(timestamp=timestamp, preferred_base=preferred_base, header_base=image_base,
                loaded_base=base, size=image_size)


def symbol_addresses(text, base):
    preferred = re.search(r'Preferred load address is\s+([0-9a-fA-F]+)', text)
    if not preferred:
        raise ValueError('Map has no preferred load address')
    preferred = int(preferred[1], 16)
    result = {}
    for line in text.splitlines():
        match = re.match(r'\s+[0-9a-fA-F]{4}:[0-9a-fA-F]+\s+(\S+)\s+([0-9a-fA-F]{16})\s', line)
        if match and match[1] in (*COUNTERS, 'shinka_cd_deadline_enabled'):
            result[match[1]] = int(match[2], 16) - preferred + base
    missing = set((*COUNTERS, 'shinka_cd_deadline_enabled')) - result.keys()
    if missing:
        raise ValueError(f'Map is missing counters: {sorted(missing)}')
    return result


def summarize(before, after):
    wall = after['wall']-before['wall']
    cpu = after['cpu']-before['cpu']
    delta = {name: after['counters'][name]-before['counters'][name] for name in COUNTERS}
    frames = delta['s_frame_count']
    if wall <= 0 or cpu < 0 or frames <= 0 or any(value < 0 for value in delta.values()):
        raise ValueError('Invalid interval: process stopped or counters/save state reset')
    if before['enabled'] != after['enabled']:
        raise ValueError('Deadline mode changed during measurement')
    return dict(wall_seconds=wall, guest_hz=frames/wall,
                process_cpu_ms_per_guest_update=cpu*1000/frames,
                process_cpu_percent_one_core=cpu/wall*100,
                deadline_fix_enabled=bool(after['enabled']),
                per_second={name: value/wall for name, value in delta.items()},
                per_guest_update={name: value/frames for name, value in delta.items()})


def collect(args):
    if not 5 <= args.seconds <= 60 or args.warmup < 6:
        raise ValueError('Use 5..60 seconds and at least 6 seconds warmup')
    if args.output.exists():
        raise FileExistsError(args.output)
    map_bytes = args.map.read_bytes()
    map_text = map_bytes.decode(errors='replace')
    addresses = symbol_addresses(map_text, args.base)
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.OpenProcess.argtypes = (w.DWORD, w.BOOL, w.DWORD)
    api.OpenProcess.restype = w.HANDLE
    api.ReadProcessMemory.argtypes = (w.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                     ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t))
    api.ReadProcessMemory.restype = w.BOOL
    api.CloseHandle.argtypes = (w.HANDLE,)
    api.CloseHandle.restype = w.BOOL
    api.QueryFullProcessImageNameW.argtypes = (w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD))
    api.QueryFullProcessImageNameW.restype = w.BOOL
    handle = api.OpenProcess(0x410, False, args.pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    clock = None
    try:
        def read_bytes(address, size):
            buffer = ctypes.create_string_buffer(size)
            got = ctypes.c_size_t()
            if not api.ReadProcessMemory(handle, address, buffer, size, ctypes.byref(got)) or got.value != size:
                raise ctypes.WinError(ctypes.get_last_error())
            return buffer.raw

        identity = validate_loaded_image(map_text, args.base, read_bytes)
        for address in addresses.values():
            if not args.base <= address <= args.base + identity['size'] - 8:
                raise ValueError('Map counter lies outside the loaded image')
        path_buffer = ctypes.create_unicode_buffer(32768)
        path_size = w.DWORD(len(path_buffer))
        if not api.QueryFullProcessImageNameW(handle, 0, path_buffer, ctypes.byref(path_size)):
            raise ctypes.WinError(ctypes.get_last_error())
        executable = Path(path_buffer.value)
        with executable.open('rb') as stream:
            def read_file(offset, size):
                stream.seek(offset)
                return stream.read(size)
            disk_identity = validate_loaded_image(map_text, 0, read_file, allow_relocated_header=False)
            if disk_identity['size'] != identity['size']:
                raise ValueError('Loaded image size differs from executable on disk')
            stream.seek(0)
            identity['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
        identity['path'] = str(executable)
        identity['map_sha256'] = hashlib.sha256(map_bytes).hexdigest()
        clock = ProcessClock(args.pid)
        nav = Navigator(args.port)
        if args.slot is not None:
            nav.call(dict(cmd='savestate', op='load', slot=args.slot))
        time.sleep(args.warmup)

        def read(name, value_type=ctypes.c_uint64):
            value = value_type()
            size = ctypes.sizeof(value)
            got = ctypes.c_size_t()
            if not api.ReadProcessMemory(handle, addresses[name], ctypes.byref(value), size, ctypes.byref(got)) or got.value != size:
                raise ctypes.WinError(ctypes.get_last_error())
            return value.value

        def snapshot():
            start = time.perf_counter()
            values = {name: read(name) for name in COUNTERS}
            return dict(wall=(start+time.perf_counter())/2, cpu=clock.seconds(),
                        counters=values, enabled=read('shinka_cd_deadline_enabled', ctypes.c_int32))

        state_before = nav.where()
        audio_before = nav.call(dict(cmd='audio_stats'))
        before = snapshot()
        time.sleep(args.seconds)
        after = snapshot()
        result = dict(schema=2, pid=args.pid, scene=args.scene, slot=args.slot, image=identity,
                      map=str(args.map.resolve()), module_base=args.base,
                      summary=summarize(before, after), before=before, after=after,
                      state_before=state_before, state_after=nav.where(),
                      audio_before=audio_before, audio_after=nav.call(dict(cmd='audio_stats')),
                      caveats=['Sequential read-only snapshots are not atomic.',
                               'SPU query/service counters indicate global scheduler visits here, not CPU time.',
                               'Latched-CD queries count redundant presentation candidates, not IRQ deliveries.',
                               '100% process CPU means one logical core.'])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
        print(json.dumps(result['summary'], indent=2), flush=True)
    finally:
        api.CloseHandle(handle)
        if clock:
            clock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--base', type=lambda value: int(value, 0), required=True)
    parser.add_argument('--map', type=Path, default=Path('build-windows/Release/dmw2003-shinka.map'))
    parser.add_argument('--scene', required=True)
    parser.add_argument('--slot', type=int, choices=range(12))
    parser.add_argument('--port', type=int, default=4380)
    parser.add_argument('--seconds', type=int, default=20)
    parser.add_argument('--warmup', type=float, default=7)
    parser.add_argument('--output', type=Path, required=True)
    collect(parser.parse_args())
