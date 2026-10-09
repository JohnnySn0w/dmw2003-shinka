"""Check consecutive battle captures for cursor tiles at the old wide anchor.

Inputs are local diagnostics, never bundled game assets: frames.bin from
menu_capture, copies.json containing frame-tagged GP0 0x80 entries, and a JSON
array of vram_peek replies covering (0,244)-(156,256). Capture the tile bank in
the same battle with raw screen colors. Use --margin 0 for a 4:3 control.
Missing cursor evidence is inconclusive, not a pass. This checks the copied command/list cursor, not every
highlight, portrait or target marker in battle.
"""
import argparse
import json
from pathlib import Path

import numpy as np

try:
    from .export_menu_capture import read_frames
except ImportError:
    from export_menu_capture import read_frames


def cursor_tiles(spans):
    bank = np.zeros((12, 156, 3), dtype=np.int16)
    covered = set()
    for span in spans:
        x, y, w, h = (span[k] for k in ('x', 'y', 'w', 'h'))
        if y != 244 or h != 12 or x < 0 or w < 1 or x+w > 156:
            raise ValueError('Expected cursor bank spans at y=244, height=12')
        data = span['hex']
        if len(data) != w*h*4:
            raise ValueError('Incomplete cursor bank')
        words = [int(data[i:i+4], 16) for i in range(0, len(data), 4)]
        pixels = [tuple(((word >> shift) & 31)*255//31 for shift in (0, 5, 10))
                  for word in words]
        bank[:, x:x+w] = np.array(pixels, dtype=np.int16).reshape(h, w, 3)
        covered.update(range(x, x+w))
    if len(covered) != 156:
        raise ValueError('All thirteen 12x12 tiles are required')
    tiles = np.array([bank[:, x:x+12] for x in range(0, 156, 12)])
    if len({tile.tobytes() for tile in tiles}) != 13:
        raise ValueError('Cursor bank is stale or incomplete: expected thirteen distinct tiles')
    return tiles


def match(patch, tiles):
    errors = np.abs(tiles-patch).mean(axis=(1, 2, 3))
    index = int(errors.argmin())
    # RGB555 expansion differs by <=1 between CPU and renderer conversions.
    return index if errors[index] < 1 else None


def check(capture, copies, tiles, margin=53):
    if not 0 <= margin <= 160:
        raise ValueError('Margin must be 0..160')
    if margin == 0:
        # Native VRAM scanout expands RGB555 with <<3; wide GPU readback uses
        # the full 0..255 range. Do not mistake that difference for lost pulses.
        tiles = ((tiles*31+127)//255)*8
    positions, sources, bands, packet_frames = set(), set(), set(), set()
    for entry in copies:
        if int(entry['op'], 16) != 0x80:
            continue
        words = [int(word, 16) for word in entry['w']]
        if len(words) != 4 or words[1] >> 16 != 244:
            continue
        sx, dx, dy = words[1] & 65535, words[2] & 65535, words[2] >> 16
        if (sx > 144 or sx % 12 or words[3] != 0x000c000c
                or dx > 308 or dy >= 496 or not 60 <= (dy & 255) <= 224):
            raise ValueError('Unrecognized cursor copy; inspect its geometry before approving')
        sources.add(sx//12)
        bands.add(dy & 256)
        positions.add((dx, dy & 255))
        packet_frames.add(entry['frame'])
    if not positions:
        raise ValueError('No cursor copies: coverage is inconclusive')
    frames, observed, old_matches, wide_matches = [], set(), [], 0
    with Path(capture).open('rb') as stream:
        for info, pixels in read_frames(stream):
            if (info['mode'] != 0x600 or info['width'] != 320+2*margin
                    or info['height'] != 240 or bool(info['wide']) != bool(margin)):
                raise ValueError('Capture must remain in the requested battle view')
            frames.append(info['frame'])
            im = np.frombuffer(pixels, dtype=np.uint8).reshape(240, info['width'], 4)[:, :, [2, 1, 0]]
            for x, y in sorted(positions):
                tile = match(im[y:y+12, x:x+12], tiles)
                if tile is not None:
                    wide_matches += 1
                    observed.add(tile)
                if margin:
                    tile = match(im[y:y+12, x+margin:x+margin+12], tiles)
                    if tile is not None:
                        old_matches.append(dict(frame=info['frame'], x=x+margin, y=y, tile=tile))
    if not frames or not packet_frames.issubset(set(frames)) or not wide_matches:
        raise ValueError('Missing or mismatched capture evidence')
    return dict(passed=not old_matches, frames=len(frames), margin=margin,
                copy_tiles=sorted(sources), framebuffer_bands=sorted(bands),
                visible_tiles=sorted(observed), correct_anchor_matches=wide_matches,
                old_anchor_matches=old_matches, positions=sorted(positions))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture_dir', type=Path)
    parser.add_argument('--tiles', type=Path, required=True)
    parser.add_argument('--margin', type=int, default=53)
    args = parser.parse_args()
    result = check(args.capture_dir/'frames.bin',
                   json.loads((args.capture_dir/'copies.json').read_text()),
                   cursor_tiles(json.loads(args.tiles.read_text())), args.margin)
    (args.capture_dir/'cursor-check.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
