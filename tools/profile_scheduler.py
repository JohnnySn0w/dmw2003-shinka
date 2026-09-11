"""Read scheduler counters from a Windows test process without suspending it.

Requires the matching executable's MSVC /MAP file and its ASLR module base.
Use a copied save profile. --slot explicitly loads a checkpoint; otherwise
the current scene is observed. No process memory is written.
"""
import argparse
import ctypes
from ctypes import wintypes as w
import json
from pathlib import Path
import re
import time

from dev_nav import Navigator
from profile_runtime import ProcessClock

COUNTERS = ('psx_cycle_count', 's_frame_count', 'g_spu_sample_deadline_queries',
            'g_spu_sample_service_checks', 'g_guest_store_count', 'g_mmio_access_count',
            'shinka_cd_deadline_queries', 'shinka_cd_latched_queries')


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
    addresses = symbol_addresses(args.map.read_text(errors='replace'), args.base)
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.OpenProcess.argtypes = (w.DWORD, w.BOOL, w.DWORD)
    api.OpenProcess.restype = w.HANDLE
    api.ReadProcessMemory.argtypes = (w.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                     ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t))
    api.ReadProcessMemory.restype = w.BOOL
    api.CloseHandle.argtypes = (w.HANDLE,)
    api.CloseHandle.restype = w.BOOL
    handle = api.OpenProcess(0x410, False, args.pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    clock = None
    try:
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
        result = dict(schema=1, pid=args.pid, scene=args.scene, slot=args.slot,
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
