"""Export a bounded menu_capture recording to numbered PNGs and metadata.

Start with the debug command {"cmd":"menu_capture","frames":120,"path":"...bin"}.
Wait until {"cmd":"menu_capture"} reports active=false and failed=0 before export.
Requires Pillow for PNG output. Captures observe vblanks, including repeated
display buffers; frame numbers make missing records detectable.
"""
import argparse
import json
from pathlib import Path
import struct

HEADER = struct.Struct('<8I')
KEYS = ('frame', 'width', 'height', 'mode', 'layout', 'wide', 'root', 'pad')


def read_frames(stream):
    if stream.read(8) != b'SHCAP001':
        raise ValueError('Not a Shinka menu capture')
    previous = None
    total = 8
    count = 0
    while header := stream.read(HEADER.size):
        if len(header) != HEADER.size:
            raise ValueError('Incomplete frame header')
        info = dict(zip(KEYS, HEADER.unpack(header)))
        width, height = info['width'], info['height']
        count += 1
        total += HEADER.size + width * height * 4
        if (width > 2048 or height > 1024 or bool(width) != bool(height)
                or count > 180 or total > 256 * 1024 * 1024):
            raise ValueError('Capture exceeds runtime bounds')
        if previous is not None and info['frame'] != (previous + 1) & 0xffffffff:
            raise ValueError('Nonconsecutive frame numbers')
        previous = info['frame']
        pixels = stream.read(width * height * 4)
        if len(pixels) != width * height * 4:
            raise ValueError('Incomplete frame pixels; capture may still be running')
        yield info, pixels


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    from PIL import Image
    args.output.mkdir(parents=True, exist_ok=True)
    metadata = []
    with args.capture.open('rb') as stream:
        for i, (info, pixels) in enumerate(read_frames(stream)):
            metadata.append(info)
            if not pixels:
                continue
            Image.frombytes('RGBA', (info['width'], info['height']), pixels,
                            'raw', 'BGRA').convert('RGB').save(args.output / f'{i:03}.png')
    (args.output / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(f'Exported {len(metadata)} consecutive frames to {args.output}')


if __name__ == '__main__':
    main()
