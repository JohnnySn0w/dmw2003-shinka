"""Repeat travel checks on copied saves; inventory native exits from RAM snapshots.

The runner uses real map cursor input. Explicit native-exit probes may position
the party with a developer warp; they never count as player fast-travel tests.
No run enables destinations or writes story/completion flags.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

try:
    from .dev_nav import Navigator, number, validate_point
    from .field_conditions import records
    from .field_triggers import TriggerMap
except ImportError:
    from dev_nav import Navigator, number, validate_point
    from field_conditions import records
    from field_triggers import TriggerMap

WATCH = ((0x8004b370, 4), (0x8004b3ac, 20), (0x8004b3de, 26))
DIRECTIONS = {'up', 'down', 'left', 'right', 'ne', 'nw', 'se', 'sw'}


def inventory(ram, step=4):
    layer = TriggerMap(ram)
    table = layer.word(0x80099d94)
    regions = layer.regions(step)
    out = []
    for region in regions:
        address = table + region['index'] * 24
        if table & 3 or not 0x80000000 <= table <= address <= 0x80200000 - 24:
            raise ValueError('Action table outside aligned guest RAM')
        action = records(ram, address - 0x80000000, 1)[0]
        row = dict(trigger=region, record=action)
        if action['action'] == 1:
            xy, orientation, _ = [int(v, 16) for v in action['remaining_words']]
            row['native_arrival'] = dict(stage=int(action['argument'], 16),
                                        x=(xy & 65535)*256, y=(xy >> 16)*256,
                                        facing=orientation & 65535)
        out.append(row)
    return dict(schema=1, stage=layer.mode, snapshot_sha256=hashlib.sha256(ram).hexdigest(),
                step=step, action_table=hex(table), triggers=out,
                limitation='Trigger-linked records only. Entry callbacks, event completion, '
                'collision and departure cleanup still need review; this is not a safety verdict.')


def validate_manifest(data):
    if data.get('schema') != 1 or not isinstance(data.get('cases'), list) or not data['cases']:
        raise ValueError('Expected schema 1 and nonempty cases')
    names = set()
    for case in data['cases']:
        name = case['name']
        if not isinstance(name, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', name) or name in names:
            raise ValueError('Case names must be unique safe directory names')
        names.add(name)
        if type(case['slot']) is not int or not 0 <= case['slot'] <= 9:
            raise ValueError('Use an existing copied checkpoint slot 0..9')
        if not 0x200 <= number(case['source']) < 0x300:
            raise ValueError('Source must be a field')
        if 'story' in case and not 0 <= number(case['story']) <= 255:
            raise ValueError('Expected story must be 0..255')
        if not isinstance(case['legs'], list) or not 1 <= len(case['legs']) <= 32:
            raise ValueError('Use 1..32 legs')
        for leg in case['legs']:
            if not 0x200 <= number(leg['stage']) < 0x300:
                raise ValueError('Destination must be a field')
            if leg['kind'] == 'map':
                if not 1 <= number(leg['icon']) <= 46:
                    raise ValueError('Map icon must be 1..46')
            elif leg['kind'] == 'native-exit':
                validate_point(leg['position'])
            else:
                raise ValueError('Use map or native-exit, never a forced map arrival')
            for key in ('x', 'y'):
                if key in leg and not 0 <= number(leg[key]) <= 0xffffff:
                    raise ValueError('Invalid expected coordinate')
            if leg.get('move') is not None:
                move = leg['move']
                if move['button'] not in DIRECTIONS or not 1 <= number(move['frames']) <= 30:
                    raise ValueError('Movement probe must be a direction for 1..30 frames')
    return data


def changed_bytes(before, after):
    if before.keys() != after.keys():
        raise ValueError('Snapshot regions differ')
    changes = []
    for address in before:
        left, right = bytes.fromhex(before[address]), bytes.fromhex(after[address])
        if len(left) != len(right):
            raise ValueError('Snapshot lengths differ')
        for i, (a, b) in enumerate(zip(left, right)):
            if a != b:
                changes.append(dict(address=hex(int(address, 16)+i), before=a, after=b))
    return changes


class TravelAudit:
    def __init__(self, nav):
        self.nav = nav

    def words(self, address, count=1):
        if address & 3 or not 0x80000000 <= address <= 0x80200000-count*4:
            raise ValueError('Map pointer outside guest RAM')
        return [int(v, 16) for v in self.nav.call(dict(cmd='mem_words', addr=hex(address), count=count))['words']]

    def map_state(self):
        if self.nav.where()['mode'] != 0x1000:
            raise RuntimeError('Map overlay no longer active')
        p = self.words(0x8005ccbc)[0]
        for index in (0, 0, 1):
            p = self.words(self.words(p+0x24)[0]+index*4)[0]
        if self.words(p+0x48)[0] != 0x8009913c:
            raise RuntimeError('Map cursor controller not ready')
        pan = self.words(p+0x90, 2)
        values = self.words(p+0x164, 9)
        def signed(v):
            return v if v < 0x80000000 else v-0x100000000
        return dict(x=signed(values[0])-signed(pan[0]), y=signed(values[1])-signed(pan[1]),
                    snapped=values[7], icon=values[8])

    def select(self, icon):
        table = self.words(0x8009af70)[0]
        _, x, y = self.words(table+12*icon, 3)
        for _ in range(100):
            s = self.map_state()
            if s['snapped'] == 1 and s['icon'] == icon:
                return s
            dx, dy = x+12-s['x'], y+12-s['y']
            button = ('right' if dx > 0 else 'left') if abs(dx) > 4 else ('down' if dy > 0 else 'up')
            distance = abs(dx) if abs(dx) > 4 else abs(dy)
            self.nav.press(button, min(8, max(1, distance//4)))
        raise RuntimeError(f'Native cursor did not select icon {icon}')

    def progression(self):
        return {hex(a): self.nav.call(dict(cmd='read_ram', addr=hex(a), len=n))['hex'] for a, n in WATCH}

    def shot(self, path):
        self.nav.call(dict(cmd='screenshot', path=str(path.resolve())))

    def control_snapshot(self, stage):
        # The mode changes before the load-in ribbon releases player input.
        # Probe Start until the real quick-menu controller reaches input phase;
        # never treat a cached return position alone as an interactive arrival.
        n = self.nav
        for _ in range(36):
            state = n.where()
            if state['mode'] != stage or state['queued']:
                raise RuntimeError('Scene interrupted arrival control check')
            if state['quick_menu'] and state['quick_phase'] == 3:
                n.press('triangle', 8)
                closed = n.until(n.where, lambda s: not s['quick_menu'], 'arrival quick-menu close')
                if closed['mode'] != stage or closed['queued']:
                    raise RuntimeError('Scene interrupted arrival quick-menu close')
                return closed
            if not state['quick_menu']:
                n.press('start', 2)
            n.press('neutral', 20)
        raise RuntimeError('Field did not accept quick-menu input within 36 probes')

    def run_leg(self, leg, folder, result):
        n = self.nav
        stage = number(leg['stage'])
        source = number(leg['position']['stage']) if leg['kind'] == 'native-exit' else n.where()['mode']
        if stage == source:
            raise ValueError('Same-stage leg cannot prove a transition occurred')
        result['kind'] = leg['kind']
        if leg['kind'] == 'native-exit':
            result['setup_before'] = self.progression()
            point = validate_point(leg['position'])
            n.open_map()
            n.mutate('warp', **point)
            n.until(n.where, lambda s: s['mode'] == point['stage'] and not s['queued'], 'native-probe field')
            result['positioned'] = self.control_snapshot(point['stage'])
            if any(result['positioned'][k] != v for k, v in point.items()):
                raise RuntimeError('Native-probe position changed on entry')
            result['setup_changes'] = changed_bytes(result['setup_before'], self.progression())
            if result['setup_changes']:
                raise RuntimeError('Native-probe positioning changed watched progression; review entry scene')
        else:
            n.open_map()
            result['selection'] = self.select(number(leg['icon']))
        self.shot(folder/'selected.png')
        result['before'] = self.progression()
        n.press('cross', 8)
        n.until(n.where, lambda s: s['mode'] == stage and not s['queued'], 'requested arrival')
        arrival = self.control_snapshot(stage)
        result['arrival'] = arrival
        if arrival['mode'] != stage or arrival['stage'] != stage or arrival['queued']:
            raise RuntimeError('Arrival changed during control check')
        for key in ('x', 'y'):
            if key in leg and arrival[key] != number(leg[key]):
                raise RuntimeError(f'Unexpected landing {key}: {arrival[key]}')
        self.shot(folder/'arrival.png')
        ram = bytes.fromhex(n.call(dict(cmd='read_ram', addr='0x80000000', len=0x200000))['hex'])
        (folder/'arrival.ram').write_bytes(ram)
        try:
            result['field'] = inventory(ram, step=8)
        except ValueError as error:
            result['inventory_error'] = str(error)
        if leg.get('move'):
            # Deferring random encounters affects only this disposable fixture.
            n.mutate('encounters', enabled=0)
            n.press(leg['move']['button'], number(leg['move']['frames']))
            moved = n.refresh()
            result['movement'] = moved
            if moved['mode'] != stage or (moved['x'], moved['y']) == (arrival['x'], arrival['y']):
                raise RuntimeError('Movement probe blocked or changed mode; review landing')
            self.shot(folder/'moved.png')
        result['after'] = self.progression()
        result['progression_changes'] = changed_bytes(result['before'], result['after'])
        if result['progression_changes']:
            raise RuntimeError('Watched story/quest bytes changed; review native event')
        result['passed'] = True

    def run(self, manifest, output):
        validate_manifest(manifest)  # Entire suite before any runtime input.
        output.mkdir(parents=True, exist_ok=False)
        (output/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        report = dict(schema=1, cases=[], watch_regions=[dict(address=hex(a), length=n) for a, n in WATCH],
                      limitation='A fixture-specific smoke test, not campaign or event-cleanup certification.')
        def save():
            (output/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        for case in manifest['cases']:
            row = dict(name=case['name'], passed=False, legs=[])
            report['cases'].append(row)
            save()
            folder = output/case['name']
            folder.mkdir()
            try:
                state = self.nav.checkpoint('load', case['slot'])
                if state['mode'] != number(case['source']) or state['queued']:
                    raise RuntimeError('Fixture does not match expected source')
                if 'story' in case and state['story'] != number(case['story']):
                    raise RuntimeError('Fixture does not match expected story')
                row['fixture'] = state
                for index, leg in enumerate(case['legs']):
                    part = dict(request=leg, passed=False)
                    row['legs'].append(part)
                    save()
                    location = folder/f'{index:02}'
                    location.mkdir()
                    self.run_leg(leg, location, part)
                    save()
                row['passed'] = True
            except (OSError, ValueError, KeyError, RuntimeError) as error:
                row['error'] = str(error)
                try:
                    self.shot(folder/'failure.png')
                except (OSError, RuntimeError) as capture_error:
                    row['capture_error'] = str(capture_error)
            finally:
                try:
                    self.nav.checkpoint('load', case['slot'])
                except (OSError, RuntimeError) as error:
                    row['passed'] = False
                    row['restore_error'] = str(error)
                    save()
                    raise RuntimeError('Fixture restore failed; stopping batch') from error
                save()
            print(f"{case['name']}: {'PASS' if row['passed'] else row.get('error', 'FAIL')}", flush=True)
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('inventory', help='Read-only batch of saved field RAM dumps')
    inspect.add_argument('snapshots', type=Path, nargs='+')
    inspect.add_argument('--step', type=int, choices=(1, 2, 4, 8), default=4)
    run = sub.add_parser('run', help='Use an already running isolated diagnostic with copied saves')
    run.add_argument('manifest', type=Path)
    run.add_argument('output', type=Path, help='New evidence directory; must not already exist')
    run.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    if args.command == 'inventory':
        print(json.dumps([dict(path=str(p), **inventory(p.read_bytes(), args.step)) for p in args.snapshots], indent=2))
        return 0
    result = TravelAudit(Navigator(args.port, timeout=45)).run(
        json.loads(args.manifest.read_text(encoding='utf-8-sig')), args.output)
    return 0 if all(case['passed'] for case in result['cases']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
