"""Measure movie delivery jitter without polling or screenshots during playback.

Use an isolated save profile. Requires the expanded Shinka latency response;
the old response silently truncates long windows and is rejected here.
"""
import argparse
import json
from pathlib import Path
import time

from dev_nav import Navigator
from profile_runtime import ProcessClock


def distribution(values):
    ordered = sorted(values)
    if not ordered:
        raise ValueError('No complete frame intervals')
    return dict(count=len(ordered), mean_ms=sum(ordered)/len(ordered),
                p50_ms=ordered[int((len(ordered)-1)*.50)],
                p95_ms=ordered[int((len(ordered)-1)*.95)],
                p99_ms=ordered[int((len(ordered)-1)*.99)], max_ms=ordered[-1],
                over_25_ms=sum(v > 25 for v in ordered),
                over_30_ms=sum(v > 30 for v in ordered),
                over_40_ms=sum(v > 40 for v in ordered))


def analyze(frames, start, end):
    # Discard the boundary frames where diagnostic requests were handled and
    # the final in-progress slot. All timestamps must share one response base.
    rows = [r for r in frames if start+2 <= r['f'] < end-1 and r['swap_end'] >= 0]
    if len(rows) < end-start-5:
        raise ValueError('Incomplete frame history: old/truncated response or missing presents')
    if any(b['f'] != a['f']+1 for a, b in zip(rows, rows[1:])):
        raise ValueError('Nonconsecutive presentation frames')
    gaps = [(b['swap_end']-a['swap_end'])/1000 for a, b in zip(rows, rows[1:])]
    if any(v <= 0 for v in gaps):
        raise ValueError('Nonmonotonic presentation timestamps')
    result = dict(delivery=distribution(gaps),
                swap=distribution([(r['swap_end']-r['swap_begin'])/1000 for r in rows]),
                before_swap=distribution([(r['swap_begin']-r['input'])/1000 for r in rows]))
    if all('begin' in r for r in rows):
        result['between_callbacks'] = distribution([
            (b['begin']-a['swap_end'])/1000 for a, b in zip(rows, rows[1:])])
        result['callback_to_paced'] = distribution([
            (r['paced']-r['begin'])/1000 for r in rows if r['paced'] >= r['begin']])
    return result


def collect(args):
    if not 5 <= args.seconds <= 60:
        raise ValueError('Use a 5..60 second interval inside the 4096-frame history')
    if args.output.exists():
        raise FileExistsError(args.output)
    nav = Navigator(args.port, timeout=45)
    clock = ProcessClock(args.pid)
    try:
        if args.slot is not None:
            nav.call(dict(cmd='savestate', op='load', slot=args.slot))
        time.sleep(7)
        audio_before = nav.call(dict(cmd='audio_stats'))
        start = nav.call(dict(cmd='latency', window=1))['summary']['frames']
        wall, cpu = time.perf_counter(), clock.seconds()
        time.sleep(args.seconds)
        elapsed, consumed = time.perf_counter()-wall, clock.seconds()-cpu
        capture = nav.call(dict(cmd='latency', raw=1, count=4096, window=4096))
        end = capture['summary']['frames']
        summary = analyze(capture['frames'], start, end)
        summary.update(wall_seconds=elapsed, cpu_seconds=consumed,
                       process_cpu_percent_one_core=consumed/elapsed*100)
        result = dict(schema=1, pid=args.pid, slot=args.slot, summary=summary,
                      first_frame=start, end_frame=end, capture=capture,
                      audio_before=audio_before, audio_after=nav.call(dict(cmd='audio_stats')),
                      caveats=['Delivery is host swap completion, not panel scanout or unique movie images.',
                               'Movie source cadence and host refresh can still cause visible judder.',
                               'Input is sampled again after pacing; before_swap excludes the pacer wait.'])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(summary, indent=2))
    finally:
        clock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--port', type=int, default=4380)
    parser.add_argument('--slot', type=int, choices=range(12))
    parser.add_argument('--seconds', type=int, default=30)
    parser.add_argument('--output', type=Path, required=True)
    collect(parser.parse_args())
