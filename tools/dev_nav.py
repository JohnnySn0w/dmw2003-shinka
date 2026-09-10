"""Navigation and fixture controls for a local Shinka debug runtime.

Run against a copied save profile. Coordinates are cached field-return values;
`where --refresh` briefly opens the quick menu to sample the current position.
"""
import argparse
import json
from pathlib import Path
import time

from runtime_probe import request

ROOT = Path(__file__).resolve().parents[1]
ROOKIES = ('Kotemon', 'Kumamon', 'Monmon', 'Agumon', 'Veemon', 'Guilmon', 'Renamon', 'Patamon')
BUTTONS = {
    'up': 0xffef, 'down': 0xffbf, 'left': 0xff7f, 'right': 0xffdf,
    'ne': 0xffcf, 'nw': 0xff6f, 'se': 0xff9f, 'sw': 0xff3f,
    'cross': 0xbfff, 'triangle': 0xefff, 'start': 0xfff7,
    'square': 0x7fff, 'circle': 0xdfff, 'l1': 0xfbff, 'r1': 0xf7ff,
    'neutral': 0xffff,
}
# Independently authored arrival coordinates shared with the validated map
# destinations. Developer warps deliberately bypass that menu's story policy.
POINTS = {
    'asuka-bridge': (0x202, 0x2dda8, 0xf760),
    'asuka-bridge-approach': (0x202, 0x27e34, 0x12bcc),
    'central-park': (0x21d, 225700, 164434),
    'wire-entrance': (0x21e, 111434, 91323),
    'wire-forest': (0x222, 87454, 66170),
    'seiryu-city': (0x22e, 0x21fda, 0x1d3d8),
    'south-station': (0x232, 0x15ade, 0x111cd),
    'bulk-bridge': (0x234, 0x3dc56, 0x1f77c),
    'tranquil-swamp': (0x237, 0x2d205, 0x106a6),
    'phoenix-bay': (0x23b, 0x437f2, 0x29469),
    'pelche-oasis': (0x249, 84211, 84884),
}


def number(value):
    return int(value, 0) if isinstance(value, str) else int(value)


def validate_point(point):
    out = {key: number(point[key]) for key in ('stage', 'x', 'y', 'facing')}
    if not (0x200 <= out['stage'] < 0x300 and 0 <= out['facing'] <= 7
            and 0 <= out['x'] <= 0xffffff and 0 <= out['y'] <= 0xffffff):
        raise ValueError('Invalid bookmark coordinates')
    return out


def load_points(path):
    points = {name: dict(zip(('stage', 'x', 'y', 'facing'), (*xyz, 0)))
              for name, xyz in POINTS.items()}
    if path.exists():
        saved = json.loads(path.read_text(encoding='utf-8'))
        if saved.get('schema') != 1 or not isinstance(saved.get('points'), dict):
            raise ValueError('Unsupported bookmark file')
        for name, point in saved['points'].items():
            if name in POINTS:
                raise ValueError(f'Bookmark shadows built-in point: {name}')
            points[name] = validate_point(point)
    return points


class Navigator:
    def __init__(self, port=4380, timeout=25, transport=request):
        self.port, self.timeout, self.transport = port, timeout, transport

    def call(self, command):
        reply = self.transport(command, self.port)
        if reply.get('ok') is not True:
            raise RuntimeError(reply.get('err') or reply.get('error') or str(reply))
        return reply

    def nav(self, op, **fields):
        return self.call(dict(cmd='shinka_nav', op=op, **fields))

    def where(self):
        state = self.nav('where')
        if state.get('schema') != 1:
            raise RuntimeError('This tool needs the Shinka navigation debug extension')
        return state

    def until(self, sample, predicate, description):
        deadline = time.monotonic() + self.timeout
        while True:
            value = sample()
            if predicate(value):
                return value
            if time.monotonic() >= deadline:
                raise TimeoutError(f'Timed out waiting for {description}: {value}')
            time.sleep(.05)

    def press(self, button, frames):
        if button not in BUTTONS or not 1 <= frames <= 300:
            raise ValueError('Use a known button and 1..300 frames')
        try:
            self.call(dict(cmd='press', buttons=BUTTONS[button], frames=frames))
            self.until(lambda: self.call(dict(cmd='pad_status')),
                       lambda s: s['override_frames'] <= 0, 'button release')
            # Neutral guest frames provide a real release edge at any turbo rate.
            self.call(dict(cmd='press', buttons=0xffff, frames=4))
            self.until(lambda: self.call(dict(cmd='pad_status')),
                       lambda s: s['override_frames'] <= 0, 'neutral input')
        finally:
            self.call(dict(cmd='clear_input'))

    def quick_menu(self):
        before = self.where()
        mode = before['mode']
        if not 0x200 <= mode < 0x300 or before['queued']:
            raise RuntimeError('Position refresh requires a stationary field mode')
        if not before['quick_menu']:
            self.press('start', 8)
        sampled = self.until(self.where, lambda s: (s['quick_menu'] and s['quick_phase'] == 3) or s['mode'] != mode,
                             'the quick menu to sample the position')
        if sampled['mode'] != mode:
            raise RuntimeError('Mode changed during position refresh')
        return sampled

    def refresh(self):
        was_open = self.where()['quick_menu']
        sampled = self.quick_menu()
        if was_open:
            return sampled
        mode = sampled['mode']
        self.press('triangle', 8)
        closed = self.until(self.where, lambda s: not s['quick_menu'], 'the quick menu to close')
        if closed['mode'] != mode or closed['queued']:
            raise RuntimeError('Mode changed while closing the quick menu')
        return closed

    def open_map(self):
        state = self.where()
        if state['mode'] == 0x1000 and not state['queued']:
            return state
        state = self.quick_menu()
        # Map is row 2 in both the original and expanded English quick list.
        for _ in range(8):
            row = state['quick_row']
            if row == 2:
                break
            self.press('down' if row < 2 else 'up', 8)
            next_state = self.where()
            check_mode(next_state, state['mode'])
            if next_state['quick_row'] == row:
                raise RuntimeError('Quick-menu cursor did not move')
            state = next_state
        if state['quick_row'] != 2:
            raise RuntimeError('Could not select the map row')
        self.press('cross', 8)
        self.until(self.where, lambda s: s['mode'] == 0x1000 and not s['queued'], 'the map overlay')
        time.sleep(2)
        return self.where()

    def mutate(self, op, **fields):
        if op == 'flag' and 'flag' in fields:
            fields['flag_id'] = fields.pop('flag')
        state = self.where()
        return self.nav(op, expected_mode=state['mode'], **fields)

    def warp(self, point):
        point = validate_point(point)
        self.open_map()
        self.mutate('warp', **point)
        time.sleep(2)  # let the old mode owner run its teardown/loader
        self.until(self.where,
                   lambda s: s['mode'] == point['stage'] and not s['queued'],
                   f"field {point['stage']:#x}")
        actual = self.refresh()
        if any(actual[key] != point[key] for key in ('stage', 'x', 'y', 'facing')):
            raise RuntimeError(f'Arrival differs from bookmark (a native event may have moved it): {actual}')
        return actual

    def checkpoint(self, op, slot):
        if not 0 <= slot <= 9:
            raise ValueError('Checkpoint slot must be 0..9')
        self.call(dict(cmd='savestate', op=op, slot=slot))
        if op == 'load':
            time.sleep(1)
        return self.where()

    def screenshot(self, path):
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.call(dict(cmd='screenshot_file', path=str(path)))
        return {'path': str(path)}

    def route(self, recipe):
        steps = validate_route(recipe)  # validate the whole route before input
        log = []
        for step in steps:
            before = self.where()
            check_mode(before, step['before'])
            self.press(step['button'], step['frames'])
            after = self.until(self.where,
                               lambda s: not s['queued'] and s['mode'] == step['after'],
                               f"route mode {step['after']:#x}")
            log.append(dict(step=step, before=before, after=after))
        return log


def check_mode(state, expected):
    if state['queued'] or state['mode'] != expected:
        raise RuntimeError(f"Route stopped: expected {expected:#x}, "
                           f"got {state['mode']:#x}, queued {state['queued']:#x}")


def validate_route(recipe):
    if recipe.get('schema') != 1 or not isinstance(recipe.get('steps'), list):
        raise ValueError('Route needs schema 1 and a steps array')
    if not 1 <= len(recipe['steps']) <= 1000:
        raise ValueError('Route needs 1..1000 steps')
    steps = []
    for step in recipe['steps']:
        item = dict(button=step['button'], frames=number(step['frames']),
                    before=number(step['before']), after=number(step['after']))
        if item['button'] not in BUTTONS or not 1 <= item['frames'] <= 300:
            raise ValueError('Invalid route button or frame count')
        if any(not 0 <= item[key] <= 0xffff for key in ('before', 'after')):
            raise ValueError('Invalid route mode')
        steps.append(item)
    return steps


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=4380)
    parser.add_argument('--bookmarks', type=Path, default=ROOT/'output/dev-nav-points.json')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('points')
    where = sub.add_parser('where')
    where.add_argument('--refresh', action='store_true')
    mark = sub.add_parser('mark')
    mark.add_argument('name')
    warp = sub.add_parser('warp')
    warp.add_argument('name')
    raw = sub.add_parser('warp-raw')
    for key in ('stage', 'x', 'y', 'facing'):
        raw.add_argument(key, type=number)
    press = sub.add_parser('press')
    press.add_argument('button', choices=BUTTONS)
    press.add_argument('frames', type=int)
    press.add_argument('--measure', action='store_true', help='Sample field coordinates before and after a directional move')
    route = sub.add_parser('route')
    route.add_argument('file', type=Path)
    for name in ('save', 'load'):
        sub.add_parser(name).add_argument('slot', type=int, choices=range(10))
    sub.add_parser('shot').add_argument('path', type=Path)
    sub.add_parser('story').add_argument('value', type=number)
    flag = sub.add_parser('flag')
    flag.add_argument('flag', type=number)
    flag.add_argument('value', type=int, choices=(0, 1))
    sub.add_parser('encounters').add_argument('mode', choices=('defer', 'next'))
    sub.add_parser('party')
    sub.add_parser('heal').add_argument('index', type=int, choices=range(8))
    power = sub.add_parser('power')
    power.add_argument('index', type=int, choices=range(8))
    power.add_argument('value', type=int)
    args = parser.parse_args(argv)
    nav = Navigator(args.port)
    try:
        cmd = args.command
        if cmd == 'points':
            result = load_points(args.bookmarks)
        elif cmd == 'where':
            result = nav.refresh() if args.refresh else nav.where()
        elif cmd == 'mark':
            if args.name in POINTS:
                raise ValueError('Choose a name other than a built-in point')
            points = load_points(args.bookmarks)
            state = nav.refresh()
            if state['stage'] != state['mode']:
                raise RuntimeError('Cached stage does not match the field')
            points[args.name] = validate_point(state)
            saved = {name: point for name, point in points.items() if name not in POINTS}
            args.bookmarks.parent.mkdir(parents=True, exist_ok=True)
            temp = args.bookmarks.with_suffix('.tmp')
            temp.write_text(json.dumps(dict(schema=1, points=saved), indent=2)+'\n', encoding='utf-8')
            temp.replace(args.bookmarks)
            result = points[args.name]
        elif cmd == 'warp':
            result = nav.warp(load_points(args.bookmarks)[args.name])
        elif cmd == 'warp-raw':
            result = nav.warp({key: getattr(args, key) for key in ('stage', 'x', 'y', 'facing')})
        elif cmd == 'press':
            if args.measure and args.button not in ('up', 'down', 'left', 'right', 'ne', 'nw', 'se', 'sw'):
                raise ValueError('Measure is for directional movement only')
            before = nav.refresh() if args.measure else None
            nav.press(args.button, args.frames)
            result = nav.refresh() if args.measure else nav.where()
            if before:
                check_mode(result, before['mode'])
                result = dict(before=before, after=result,
                              dx=result['x']-before['x'], dy=result['y']-before['y'],
                              frames=args.frames)
        elif cmd == 'route':
            result = nav.route(json.loads(args.file.read_text(encoding='utf-8')))
        elif cmd in ('save', 'load'):
            result = nav.checkpoint(cmd, args.slot)
        elif cmd == 'shot':
            result = nav.screenshot(args.path)
        elif cmd == 'party':
            result = nav.nav('party')
        else:
            fields = {key: getattr(args, key) for key in ('value', 'flag', 'index') if hasattr(args, key)}
            if cmd == 'encounters':
                fields['enabled'] = int(args.mode == 'next')
            nav.mutate(cmd, **fields)
            result = nav.nav('party') if cmd in ('heal', 'power') else nav.where()
        if isinstance(result, dict) and 'partners' in result:
            for partner in result['partners']:
                partner['name'] = ROOKIES[partner['index']]
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        parser.exit(1, f'dev-nav: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
