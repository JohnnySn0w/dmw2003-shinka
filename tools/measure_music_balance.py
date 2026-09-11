"""Measure dry music-role balance in a running copied-profile debug session.

Reloads each checkpoint per palette and temporarily changes Soundtrack. Records
post-envelope/pan RMS before reverb, CD audio, main volume and bus clipping.
Role labels describe provisional pack routes, not verified instrument identity.
"""
import argparse
import json
import math
from pathlib import Path
import time

from capture_music_balance import scene
from dev_nav import Navigator

ROLES = ('melody', 'bass', 'percussion', 'unclassified')
PALETTES = ('Original', 'DS', 'Sampled', 'Chip')


def relative_db(value, reference):
    return 20 * math.log10(value / reference) if value > 0 and reference > 0 else None


def report(records):
    lines = ['# Dry music-role balance', '',
             'RMS is measured after envelopes and voice panning, before reverb, '
             'main volume and bus clipping. Role groups follow the pack routing. '
             'Unclassified includes unmatched voices, noise and untagged packs. '
             'These short sequential replays are not sample-aligned stems or a listening verdict.', '',
             '| Scene | Palette | Melody RMS | Bass vs melody | Percussion vs melody | Unclassified RMS |',
             '| --- | --- | ---: | ---: | ---: | ---: |']
    def db(value):
        return 'silent / undefined' if value is None else f'{value:+.1f} dB'
    for row in records:
        melody, bass, drums, other = row['meter']['rms']
        lines.append(f"| {row['scene']} | {PALETTES[row['palette']]} | {melody:.1f} | "
                     f'{db(relative_db(bass, melody))} | {db(relative_db(drums, melody))} | {other:.1f} |')
    return '\n'.join(lines) + '\n'


def measure(output, scenes, seconds=8, port=4380):
    if not scenes or not 1 <= seconds <= 30 or len({name for name, _ in scenes}) != len(scenes):
        raise ValueError('Use 1..30 seconds and distinct scene names')
    if any(not 0 <= slot <= 9 for _, slot in scenes):
        raise ValueError('Use an existing checkpoint slot 0..9')
    nav = Navigator(port, timeout=seconds + 10)
    previous = nav.nav('music')['palette']
    output.mkdir(parents=True, exist_ok=False)
    records = []
    try:
        for name, slot in scenes:
            for palette in range(4):
                state = nav.checkpoint('load', slot)
                nav.nav('music', palette=palette)
                time.sleep(.5)  # settle the palette crossfade before metering
                frames = round(seconds * 44100)
                nav.nav('music-meter', frames=frames)
                meter = nav.until(lambda: nav.nav('music-meter'),
                                  lambda m: not m['active'], 'the dry music meter')
                music = nav.nav('music')
                after = nav.where()
                if meter['frames'] != frames or music['palette'] != palette or not music['matched_notes']:
                    raise RuntimeError('Meter interrupted, palette changed, or no matched music')
                if after['mode'] != state['mode'] or after['queued']:
                    raise RuntimeError('Scene changed during metering; use an idle checkpoint')
                records.append(dict(scene=name, slot=slot, palette=palette,
                                    meter=meter, music=music, state=state))
                (output / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')
                (output / 'balance.md').write_text(report(records))
                print(f'{name}: {PALETTES[palette]}, {frames} dry frames', flush=True)
    finally:
        try:
            nav.nav('music-meter', frames=0)
        finally:
            nav.nav('music', palette=previous)
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scene', type=scene, action='append', required=True)
    parser.add_argument('--seconds', type=float, default=8)
    parser.add_argument('--port', type=int, default=4380)
    args = parser.parse_args()
    measure(args.output, args.scene, args.seconds, args.port)
