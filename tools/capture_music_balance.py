"""Capture each live palette at copied-profile checkpoints for mix comparisons.

The runtime must already be running with a diagnostic save profile. This loads
the requested states and changes the shared soundtrack setting temporarily.
Audio ranges use the SPU sample clock: an omitted start exports the oldest ring
audio, not the most recent audio, and is unsuitable for palette comparisons.
"""
import argparse
import json
from pathlib import Path
import re
import time

from dev_nav import Navigator


def scene(value):
    if not re.fullmatch(r'[a-z0-9_-]+:\d+', value):
        raise argparse.ArgumentTypeError('Use scene-name:checkpoint-slot')
    name, slot = value.split(':')
    if not 0 <= int(slot) <= 10:
        raise argparse.ArgumentTypeError('Use an existing checkpoint slot 0..10')
    return name, int(slot)


def capture(output, scenes, seconds=8, port=4380):
    if not 1 <= seconds <= 30 or len({name for name, _ in scenes}) != len(scenes):
        raise ValueError('Use 1..30 seconds and distinct scene names')
    output.mkdir(parents=True, exist_ok=False)
    nav = Navigator(port, timeout=seconds+10)
    previous = nav.nav('music')['palette']
    records = []
    try:
        for name, slot in scenes:
            for palette in range(4):
                nav.call(dict(cmd='savestate', op='load', slot=slot))
                time.sleep(.5)
                nav.nav('music', palette=palette)
                head = nav.call(dict(cmd='audio_stats'))['taps'][0]
                if head['rate'] != 44100:
                    raise RuntimeError('Expected native SPU rate')
                start = head['frames']+22050  # allow the instrument fade to settle
                count = round(seconds*44100)
                nav.until(lambda: nav.call(dict(cmd='audio_stats'))['taps'][0]['frames'],
                          lambda total: total >= start+count, 'the audio capture window')
                path = (output/f'{name}-{palette}.wav').resolve()
                result = nav.call(dict(cmd='audio_wav', tap=0, path=str(path),
                                       start=str(start), count=count))
                if result['frames'] != count:
                    raise RuntimeError('Incomplete audio capture')
                music = nav.nav('music')
                if music['palette'] != palette or not music['matched_notes']:
                    raise RuntimeError('Palette changed or scene has no matched music notes')
                result.update(scene=name, slot=slot, palette=palette, start=start,
                              music=music, state=nav.where())
                records.append(result)
                (output/'captures.json').write_text(json.dumps(records, indent=2)+'\n')
                print(f'{name}: palette {palette}, {count} frames', flush=True)
    finally:
        nav.nav('music', palette=previous)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scene', type=scene, action='append', required=True)
    parser.add_argument('--seconds', type=float, default=8)
    parser.add_argument('--port', type=int, default=4380)
    args = parser.parse_args()
    capture(args.output, args.scene, args.seconds, args.port)
