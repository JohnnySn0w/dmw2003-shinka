"""Record a short real-time showcase from an already isolated debug runtime.

Recipes contain seconds and optional inputs: {"at": 2, "button": "cross"}.
This does not load saves or directly edit story flags. Use a copied profile.
Native frames retain PAL vblank timing, including gaps between capture chunks.
Audio uses the SPU sample clock, aligned at capture start to within one vblank.
Requires Pillow and ffmpeg. Raw frames and metadata stay in ignored output/.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

from dev_nav import BUTTONS, Navigator
from export_menu_capture import read_frames
from PIL import Image


def record(output, seconds, events=(), port=4385, audio=False):
    output = Path(output).resolve()
    root = Path(__file__).resolve().parents[1] / 'output'
    if not output.is_relative_to(root) or not 1 <= seconds <= 45:
        raise ValueError('Use a new output/ directory and 1..45 seconds')
    events = sorted(events, key=lambda event: event['at'])
    for event in events:
        if not 0 <= event['at'] < seconds or event['button'] not in BUTTONS:
            raise ValueError('Invalid input event')
    output.mkdir(parents=True, exist_ok=False)
    nav = Navigator(port)

    def clock():
        tap = nav.call(dict(cmd='audio_stats'))['taps'][0]
        if tap['rate'] != 44100:
            raise RuntimeError('Expected 44.1 kHz SPU clock')
        return tap['frames']

    start = clock()
    frames, inputs = [], []
    pending = list(events)
    chunks = []
    active = False
    release_at = None
    wall_start = time.monotonic()
    try:
        while (clock() - start) / 44100 < seconds:
            stamp = clock()
            elapsed = (stamp - start) / 44100
            if time.monotonic() - wall_start > seconds * 3 + 10:
                raise RuntimeError('Capture clock stalled')
            if release_at is not None and elapsed >= release_at:
                nav.call(dict(cmd='clear_input'))
                release_at = None
            while pending and elapsed >= pending[0]['at']:
                event = pending.pop(0)
                nav.call(dict(cmd='press', buttons=BUTTONS[event['button']], frames=8))
                release_at = elapsed + .22
                inputs.append(dict(event, actual=elapsed))
            if active:
                status = nav.call(dict(cmd='menu_capture'))
                if status['failed']:
                    raise RuntimeError('Native frame capture failed')
                active = status['active']
            if not active:
                path = output / f'chunk-{len(chunks):03}.bin'
                count = max(1, min(150, round((seconds-elapsed)*50)))
                nav.call(dict(cmd='menu_capture', frames=count, path=str(path)))
                chunks.append(path)
                active = True
            time.sleep(.035)
        nav.until(lambda: nav.call(dict(cmd='menu_capture')),
                  lambda status: not status['active'], 'last capture chunk')
        end = clock()
        wall_seconds = time.monotonic() - wall_start
        if audio:
            result = nav.call(dict(cmd='audio_wav', tap=0, path=str(output/'audio.wav'),
                                   start=str(start), count=end-start))
            if result['frames'] != end-start:
                raise RuntimeError('Audio ring did not retain the full clip')
    finally:
        nav.call(dict(cmd='clear_input'))
    first_frame = None
    for chunk in chunks:
        with chunk.open('rb') as stream:
            for info, pixels in read_frames(stream):
                if first_frame is None:
                    first_frame = info['frame']
                # PAL vblank cadence; preserve gaps between bounded chunks.
                stamp = ((info['frame'] - first_frame) & 0xffffffff) / 50
                if not pixels:
                    image = Image.new('RGB', (426, 240))
                else:
                    image = Image.frombytes('RGBA', (info['width'], info['height']),
                                            pixels, 'raw', 'BGRA').convert('RGB')
                path = output / f'{len(frames):05}.png'
                image.save(path, compress_level=1)
                frames.append(dict(path=path.name, time=stamp, frame=info['frame']))
    duration = (end-start)/44100
    frames = [frame for frame in frames if frame['time'] < duration]
    metadata = dict(duration=duration, wall_seconds=wall_seconds,
                    frames=frames, inputs=inputs, state=nav.where(), music=nav.nav('music'))
    (output/'recording.json').write_text(json.dumps(metadata, indent=2)+'\n')
    # ffconcat file paths are local numeric names, avoiding shell/path quoting.
    lines = []
    for i, frame in enumerate(frames):
        begin = frame['time'] if i else 0
        finish = frames[i+1]['time'] if i+1 < len(frames) else duration
        lines.extend([f"file '{frame['path']}'", 'option framerate 50', f'duration {finish-begin:.6f}'])
    lines.extend([f"file '{frames[-1]['path']}'", 'option framerate 50'])
    (output/'frames.txt').write_text('\n'.join(lines)+'\n')
    # Preserve native pixel pitch; center 4:3 frames if a clip changes view.
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat',
               '-safe', '0', '-i', 'frames.txt']
    if audio:
        command += ['-i', 'audio.wav']
    filters = ('pad=426:240:(ow-iw)/2:(oh-ih)/2,scale=852:480:flags=neighbor,'
               'fps=50,tpad=stop_mode=clone:stop_duration=1')
    command += ['-vf', filters,
                '-r', '50', '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p',
                '-threads', '2', '-t', str(duration), '-movflags', '+faststart']
    command += ['-c:a', 'aac', '-b:a', '160k'] if audio else ['-an']
    subprocess.run(command+['clip.mp4'], cwd=output, check=True)
    return metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--seconds', type=float, required=True)
    parser.add_argument('--recipe', type=Path)
    parser.add_argument('--port', type=int, default=4385)
    parser.add_argument('--audio', action='store_true')
    args = parser.parse_args()
    recipe = json.loads(args.recipe.read_text()) if args.recipe else []
    result = record(args.output, args.seconds, recipe, args.port, args.audio)
    print(f"Recorded {result['duration']:.2f}s, {len(result['frames'])} frames")
