"""Profile a running Windows diagnostic game without changing its settings.

Use a copied save profile. --slot explicitly loads a checkpoint; omit it to
measure the current scene. Launch with PSX_RUNTIME_PERF_DIAG=1 for the companion
cadence log. CPU seconds come from Windows, not the runtime's wall-time stamps.
"""
import argparse
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import time

from dev_nav import Navigator


class ProcessClock:
    def __init__(self, pid):
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        self.api.OpenProcess.restype = wintypes.HANDLE
        self.api.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),)*4
        self.api.GetProcessTimes.restype = wintypes.BOOL
        self.api.CloseHandle.argtypes = (wintypes.HANDLE,)
        self.api.CloseHandle.restype = wintypes.BOOL
        self.handle = self.api.OpenProcess(0x1000, False, pid)  # query limited information
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())

    def seconds(self):
        times = [wintypes.FILETIME() for _ in range(4)]
        if not self.api.GetProcessTimes(self.handle, *(ctypes.byref(t) for t in times)):
            raise ctypes.WinError(ctypes.get_last_error())
        return sum((t.dwHighDateTime << 32) | t.dwLowDateTime for t in times[2:]) / 10_000_000

    def close(self):
        self.api.CloseHandle(self.handle)


def snapshot(nav, clock):
    start = time.perf_counter()
    frame = nav.call(dict(cmd='frame'))['frame']
    cpu = clock.seconds()
    end = time.perf_counter()
    return dict(wall=(start+end)/2, cpu_seconds=cpu, frame=frame,
                query_wall_seconds=end-start)


def summarize(first, last):
    wall = last['wall']-first['wall']
    cpu = last['cpu_seconds']-first['cpu_seconds']
    frames = last['frame']-first['frame']
    if wall <= 0 or cpu < 0 or frames <= 0:
        raise ValueError('Invalid profiling interval: clock/frame reset or game stopped')
    return dict(wall_seconds=wall, cpu_seconds=cpu, guest_frames=frames,
                guest_hz=frames/wall, process_cpu_ms_per_guest_frame=cpu*1000/frames,
                process_cpu_percent_one_core=cpu/wall*100)


def collect(args):
    if not 5 <= args.seconds <= 60 or args.warmup < 6:
        raise ValueError('Use 5..60 seconds and at least 6 seconds of warmup')
    if args.output.exists():
        raise FileExistsError(args.output)
    nav = Navigator(args.port)
    clock = ProcessClock(args.pid)
    try:
        if args.slot is not None:
            nav.call(dict(cmd='savestate', op='load', slot=args.slot))
        # The frame_perf ring holds 256 frames (~5.12 s at PAL cadence).
        time.sleep(args.warmup)
        state = nav.where()
        audio_before = nav.call(dict(cmd='audio_stats'))
        interpreter_before = nav.call(dict(cmd='dirty_ram_stats'))
        hot_before = {s: nav.call(dict(cmd='phase_hot', set=s, top=64))
                      for s in ('static', 'native')}
        samples = [snapshot(nav, clock)]
        deadline = time.perf_counter()+args.seconds
        while time.perf_counter() < deadline:
            time.sleep(min(1, max(0, deadline-time.perf_counter())))
            samples.append(snapshot(nav, clock))
        summary = summarize(samples[0], samples[-1])
        result = dict(schema=1, scene=args.scene, slot=args.slot, pid=args.pid,
                      summary=summary, samples=samples, state_before=state,
                      state_after=nav.where(), audio_before=audio_before,
                      audio_after=nav.call(dict(cmd='audio_stats')),
                      interpreter_before=interpreter_before,
                      interpreter_after=nav.call(dict(cmd='dirty_ram_stats')),
                      overlay_loader=nav.call(dict(cmd='overlay_loader_status')),
                      phase=nav.call(dict(cmd='phase_profile', window=args.seconds-1)),
                      hot_before=hot_before,
                      hot_after={s: nav.call(dict(cmd='phase_hot', set=s, top=64))
                                 for s in ('static', 'native')},
                      frame_perf=nav.transport(dict(cmd='frame_perf'), nav.port),
                      music=nav.nav('music'), view=nav.nav('view'),
                      idle_skip=nav.call(dict(cmd='idle_skip')),
                      caveats=[
                          'Process CPU includes all game and driver threads; 100% means one logical core.',
                          'phase_profile samples wall time, including waits under the current phase stamp.',
                          'phase_hot is cumulative and limited to 64 entries; do not treat it as a CPU profile.',
                          'frame_perf emu_cpu includes pacing; GL elapsed brackets can include GPU idle gaps.',
                          'frame_perf is a recent ring, not the full measurement window.',
                          'Diagnostic instrumentation adds overhead; compare with GL timers disabled.',
                      ])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
        print(json.dumps(dict(scene=args.scene, **summary)), flush=True)
    finally:
        clock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--scene', required=True)
    parser.add_argument('--slot', type=int, choices=range(12))
    parser.add_argument('--port', type=int, default=4380)
    parser.add_argument('--seconds', type=int, default=10)
    parser.add_argument('--warmup', type=float, default=7)
    parser.add_argument('--output', type=Path, required=True)
    collect(parser.parse_args())
