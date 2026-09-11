"""Summarize a bounded battle write trace and its preceding 2 MiB RAM snapshot.

Offline only. Object ownership is established at snapshot time, not guaranteed
throughout the recording. This reports observed events, not simulated speedups.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

from inspect_runtime_objects import canonical, inspect_objects, ram_offset


def number(value):
    if isinstance(value, str):
        value = int(value, 0)
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError('Expected an unsigned 32-bit integer')
    return value


def offset(value, length=4):
    result = ram_offset(number(value), length)
    if result is None:
        raise ValueError('Expected aligned main RAM address')
    return result


def validate_trace(capture):
    """Reject lost/reordered writes and inconsistent overlapping byte histories."""
    entries = capture['trace']
    if not entries:
        raise ValueError('Empty trace')
    spans = [(offset(lo, 0), offset(hi, 0)) for lo, hi in capture['spans']]
    if not spans or any(lo >= hi for lo, hi in spans):
        raise ValueError('Invalid watched ranges')
    normalized, seen = [], {}
    previous_frame = 0
    for index, raw in enumerate(entries):
        e = {key: number(raw[key]) for key in ('seq', 'frame', 'addr', 'pc', 'ra', 'old', 'new', 'w')}
        if e['seq'] != index or e['frame'] < previous_frame:
            raise ValueError('Trace must start at sequence zero and contain ordered, consecutive writes')
        previous_frame = e['frame']
        width = e['w']
        # Width-aligned RAM addresses may be halfwords or bytes, unlike headers.
        address = offset(e['addr'] & ~3, 4) + (e['addr'] & 3)
        if width not in (1, 2, 4) or address % width or address + width > 0x200000:
            raise ValueError('Invalid write width/alignment')
        if not any(lo <= address and address + width <= hi for lo, hi in spans):
            raise ValueError('Write lies outside the declared watched ranges')
        if max(e['old'], e['new']) >= 1 << (width * 8):
            raise ValueError('Write value exceeds its width')
        for byte in range(width):
            old = (e['old'] >> (8 * byte)) & 255
            if address + byte in seen and seen[address + byte] != old:
                raise ValueError(f'Broken old/new continuity at sequence {index}')
            seen[address + byte] = (e['new'] >> (8 * byte)) & 255
        e['addr'] = address
        e['pc'] = offset(e['pc'])
        e['ra'] = canonical(e['ra']) or f"0x{e['ra']:08X}"
        normalized.append(e)
    counts = capture.get('recorder')
    if counts is not None:
        if any(number(counts[key]) != len(entries) for key in ('total', 'available')):
            raise ValueError('Recorder totals do not match the retained trace')
    return normalized, spans, counts is not None


def discover(ram):
    graph = inspect_objects(ram)
    if graph['mode'] != 0x600 or not graph['owner_found']:
        raise ValueError('Snapshot must contain a recognized battle mode owner')
    objects = {obj['address']: obj for obj in graph['objects']}
    actors, cameras = {}, []
    for obj in objects.values():
        if not obj['reachable']:
            continue
        if obj['callback'] == '0x80091DF4':
            cameras.append(offset(obj['address']))
        if obj['callback'] != '0x80087BB0':
            continue
        for child in obj['children']:
            model = objects.get(child['address'])
            if not model or model['callback'] != '0x80083E0C':
                continue
            address = offset(model['address'], 0xa4)
            control = offset(struct.unpack_from('<I', ram, address + 0x64)[0], 0x28)
            if control == 0:
                raise ValueError('Combatant has a null control pointer')
            actors[address] = dict(address=canonical(address), control=canonical(control),
                                   group=obj['address'], slot=child['slot'])
    if not actors:
        raise ValueError('No combatant models under a reachable combatant group')
    return actors, cameras


def histogram(counter):
    return {str(key): value for key, value in sorted(counter.items())}


def signed(value):
    return value - 0x100000000 if value & 0x80000000 else value


def analyze_scripts(capture, ram, entries, spans):
    """Decode watched allocation leads only while their callback owns a script.

    Register observations are tied to individual verified store sites. Commands
    report parsed requests, not proof that the effect/sound subsequently ran.
    """
    scripts = [offset(value, 0xb4) for value in capture.get('scripts', [])]
    if len(scripts) != len(set(scripts)):
        raise ValueError('Duplicate script allocation leads')
    states, reports, events = {}, [], []
    for address in scripts:
        if not any(lo <= address and address + 0xb4 <= hi for lo, hi in spans):
            raise ValueError('Script allocation needs complete header/payload watch coverage')
        first = next((e for e in entries if e['addr'] == address + 0x48 and e['w'] == 4), None)
        callback = first['old'] if first else struct.unpack_from('<I', ram, address + 0x48)[0]
        report = dict(address=canonical(address), initial_callback=f'0x{callback:08X}',
                      initial_callback_source='first_store_old' if first else 'snapshot',
                      lifetimes=[], commands=[], waits=Counter(), ignored_non_script_writes=0)
        reports.append(report)
        states[address] = dict(callback=callback, epoch=0, report=report, command=None)
        if canonical(callback) == '0x8008C590':
            report['lifetimes'].append(dict(epoch=0, start_seq=0, start_frame=entries[0]['frame'],
                                            began_before_capture=True))

    for e, raw in zip(entries, capture['trace']):
        for address, state in states.items():
            if not address <= e['addr'] < address + 0xb4:
                continue
            relative = e['addr'] - address
            report = state['report']
            active = canonical(state['callback']) == '0x8008C590'
            if relative & ~3 in (0x48, 0x8c, 0x9c) and e['w'] != 4:
                raise ValueError('Partial script field writes need a new decoder')
            kind, details = None, {}
            if relative == 0x48:
                now_active = canonical(e['new']) == '0x8008C590'
                state['callback'] = e['new']
                if active and not now_active:
                    report['lifetimes'][-1].update(end_seq=e['seq'], end_frame=e['frame'],
                                                   ended_by='callback_replaced')
                    kind = 'script_deactivated'
                    state['command'] = None
                elif now_active and not active:
                    state['epoch'] += 1
                    report['lifetimes'].append(dict(epoch=state['epoch'], start_seq=e['seq'],
                                                    start_frame=e['frame'], began_before_capture=False))
                    kind = 'script_activated'
            elif not active:
                report['ignored_non_script_writes'] += 1
                continue
            elif relative in (0x8c, 0x9c):
                pc = e['pc']

                def register(name):
                    if name not in raw:
                        raise ValueError(f'Missing {name} register at script store {canonical(pc)}')
                    return number(raw[name])

                if relative == 0x8c and pc == 0x8c724:
                    if canonical(register('s1')) != canonical(address):
                        raise ValueError('Script cursor writer register does not match its allocation')
                    opcode = signed(register('v1'))
                    command = state['command']
                    cursor = canonical(e['old'] & ~3)
                    if cursor is None or e['old'] & 1:
                        raise ValueError('Script command cursor is outside halfword-aligned main RAM')
                    cursor = f"0x{0x80000000 + (e['old'] & 0x1fffffff):08X}"
                    if command is None or (command['cursor'], command['opcode']) != (cursor, opcode):
                        command = dict(epoch=state['epoch'], cursor=cursor, opcode=opcode,
                                       first_frame=e['frame'], last_frame=e['frame'], attempts=0)
                        report['commands'].append(command)
                        state['command'] = command
                        kind, details = 'script_command_entered', dict(cursor=cursor, opcode=opcode)
                    command['last_frame'] = e['frame']
                    command['attempts'] += 1
                elif relative == 0x8c and pc in (0x8bb14, 0x8bdd0, 0x8be74, 0x8c438):
                    if pc == 0x8bb14:
                        opcode = register('s1')
                        kind = 'clip_completion_wait' if opcode == 0 else f'actor_command_{opcode}_wait'
                    else:
                        kind = 'effect_resource_wait'
                    report['waits'][kind] += 1
                elif relative == 0x9c and pc == 0x8c268:
                    kind, details = 'script_delay_started', dict(duration=signed(e['new']))
                elif relative == 0x9c and pc == 0x8c28c:
                    report['waits']['script_delay_updates'] += 1
                    if signed(e['old']) > 0 and signed(e['new']) <= 0:
                        kind = 'script_delay_elapsed'
                elif relative == 0x8c and pc == 0x8c480:
                    kind, details = 'sound_command', dict(selector=signed(register('a0')),
                                                         argument=signed(register('a1')))
                elif relative == 0x8c and pc == 0x8c31c:
                    kind, details = 'effect_command', dict(selector=signed(register('s0')),
                                                          operation=signed(register('a2')))
            if kind:
                events.append(dict(seq=e['seq'], frame=e['frame'], script=canonical(address),
                                   epoch=state['epoch'], kind=kind, old=e['old'], new=e['new'],
                                   pc=canonical(e['pc']), caller=e['ra'], **details))
    for report in reports:
        report['waits'] = histogram(report['waits'])
        if report['lifetimes'] and 'end_seq' not in report['lifetimes'][-1]:
            report['lifetimes'][-1].update(end_seq=entries[-1]['seq'], end_frame=entries[-1]['frame'],
                                           ended_by='capture_end')
    return reports, events


def analyze_battle_stats(ram, entries, spans):
    """Report the supported battle-local stat table, distinct from party saves."""
    records, events = [], []
    for slot in range(6):
        address = 0xa4470 + slot * 0x20
        if not any(lo <= address and address + 0x20 <= hi for lo, hi in spans):
            continue
        words = struct.unpack_from('<16H', ram, address)
        records.append(dict(slot=slot, address=canonical(address), resource_id=words[0],
                            snapshot_hp=words[4], max_hp=words[3],
                            snapshot_mp=words[6], max_mp=words[5]))
    slots = {0xa4470 + record['slot'] * 0x20: record['slot'] for record in records}
    result_watched = any(lo <= 0xa441c and 0xa4420 <= hi for lo, hi in spans)
    for e in entries:
        if result_watched and e['addr'] < 0xa4420 and e['addr'] + e['w'] > 0xa441c:
            if e['addr'] != 0xa441c or e['w'] != 4:
                raise ValueError('Partial damage-result writes need a new decoder')
            kind = {0x9e234: 'basic_damage_prepared', 0x9e378: 'technique_damage_prepared'}.get(
                e['pc'], 'damage_result_write')
            events.append(dict(seq=e['seq'], frame=e['frame'], kind=kind,
                               old=e['old'], new=e['new'], pc=canonical(e['pc']), caller=e['ra']))
        address = 0xa4470 + ((e['addr'] - 0xa4470) // 0x20) * 0x20
        if address not in slots:
            continue
        relative = e['addr'] - address
        # Do not silently miss byte/word writes overlapping a decoded halfword.
        if not any(relative < field + 2 and relative + e['w'] > field for field in (8, 12)):
            continue
        if e['w'] != 2 or relative not in (8, 12):
            raise ValueError('Non-halfword battle HP/MP writes need a new decoder')
        field = 'hp' if relative == 8 else 'mp'
        kind = {0x8d064: 'basic_hp_subtract', 0x8d074: 'basic_hp_clamp',
                0x8fbc0: 'technique_hp_subtract', 0x8fbd4: 'technique_hp_clamp'}.get(e['pc'])
        if kind and field != 'hp':
            raise ValueError('Known HP store wrote a different battle stat')
        event = dict(seq=e['seq'], frame=e['frame'], battle_slot=slots[address],
                     kind=kind or f'battle_{field}_write', old=e['old'], new=e['new'],
                     pc=canonical(e['pc']), caller=e['ra'])
        if field == 'hp':
            # A negative intermediate HP is followed by a clamp, not a heal.
            event['new_signed'] = e['new'] - 0x10000 if e['new'] & 0x8000 else e['new']
        events.append(event)
    return records, events


def analyze(capture, ram):
    entries, spans, has_totals = validate_trace(capture)
    actors, camera_addresses = discover(ram)
    models = [offset(value) for value in capture['models']]
    controls = [offset(value) for value in capture['controls']]
    if not models or len(set(models)) != len(models) or len(models) != len(controls):
        raise ValueError('Expected distinct model/control pairs')
    for model, control in zip(models, controls):
        if model not in actors or canonical(control) != actors[model]['control']:
            raise ValueError('Trace model/control does not match snapshot combatant ownership')

    def covered(address, size=4):
        return any(lo <= address and address + size <= hi for lo, hi in spans)

    fields = {}
    summaries = []
    counters = []
    for index, (model, control) in enumerate(zip(models, controls)):
        watched = {model + 0x78: 'clip', model + 0x7c: 'completion',
                   model + 0x80: 'position', control + 8: 'request',
                   control + 0xc: 'restart', control + 0x10: 'notification'}
        for address, field in watched.items():
            if address in fields or not covered(address):
                raise ValueError('Overlapping actors or missing model/control watch coverage')
            fields[address] = (index, field)
        # The snapshot precedes arming: the first clip store's OLD value is a
        # stronger initial seed when available. Do not seed all writes from RAM.
        first_clip = next((e for e in entries if e['addr'] == model + 0x78 and e['w'] == 4), None)
        clip = first_clip['old'] if first_clip else struct.unpack_from('<I', ram, model + 0x78)[0]
        summaries.append(dict(**actors[model], initial_clip=clip,
                              initial_clip_source='first_store_old' if first_clip else 'snapshot',
                              clip_sequence=[clip], segments=[], events=[]))
        counters.append(Counter())

    cameras = {address: dict(address=canonical(address),
                            service_id=struct.unpack_from('<I', ram, address + 0x50)[0],
                            progress_writers=Counter(), setter_callers=Counter(),
                            interpolation_updates=0, direct_sets=0, events=[])
               for address in camera_addresses if covered(address + 0xf0)}
    current = [dict(clip=s['initial_clip'], start_frame=entries[0]['frame'],
                    start_seq=0, began_before_capture=True, loops=0, completions=0)
               for s in summaries]
    events = []
    shared_steps = Counter()
    for e in entries:
        address, pc = e['addr'], e['pc']
        if address == 0xa4464 and e['w'] == 4:
            shared_steps[e['new']] += 1
        for camera_address, camera in cameras.items():
            if address == camera_address + 0xf0 and e['w'] == 4:
                camera['progress_writers'][canonical(pc)] += 1
                if pc == 0x92290:
                    camera['direct_sets'] += 1
                    camera['setter_callers'][e['ra']] += 1
                elif pc == 0x91ee0:
                    camera['interpolation_updates'] += 1
                kind = {0x92290: 'camera_direct_set', 0x91ee0: 'camera_advance'}.get(
                    pc, 'other_camera_progress_write')
                event = dict(seq=e['seq'], frame=e['frame'], camera=canonical(camera_address),
                             kind=kind, old=e['old'], new=e['new'], pc=canonical(pc), caller=e['ra'])
                camera['events'].append(event)
                events.append(event)
        field_address = address & ~3
        if field_address not in fields:
            continue
        if e['w'] != 4:
            raise ValueError('Partial model/control field writes need a new decoder')
        index, field = fields[field_address]
        summary, segment = summaries[index], current[index]
        kind = None
        if field == 'clip':
            segment.update(end_frame=e['frame'], end_seq=e['seq'], ended_by='clip_selection')
            summary['segments'].append(segment)
            current[index] = dict(clip=e['new'], start_frame=e['frame'], start_seq=e['seq'],
                                  began_before_capture=False, loops=0, completions=0)
            if e['new'] != summary['clip_sequence'][-1]:
                summary['clip_sequence'].append(e['new'])
            kind = 'clip_selected' if e['new'] != e['old'] else 'same_clip_selected'
        elif field == 'position':
            if pc == 0x83d3c:
                counters[index][e['new'] - e['old']] += 1
            elif pc == 0x83d88:
                kind = 'loop'
                segment['loops'] += 1
            elif pc == 0x83d4c:
                kind = 'end_clamp'
            elif pc not in (0x83a98, 0x83c0c) and e['new'] != e['old']:
                kind = 'other_position_write'
        elif e['new'] != e['old']:
            if field == 'completion' and e['new']:
                kind = 'completion_set'
                segment['completions'] += 1
            elif field == 'notification' and e['new']:
                kind = 'completion_notified'
            elif field == 'request':
                kind = 'clip_requested'
            elif field == 'restart' and e['new']:
                kind = 'restart_requested'
        if kind:
            event = dict(seq=e['seq'], frame=e['frame'], actor=index, kind=kind,
                         clip=current[index]['clip'], old=e['old'], new=e['new'],
                         pc=canonical(pc), caller=e['ra'])
            summary['events'].append(event)
            events.append(event)
    for index, summary in enumerate(summaries):
        current[index].update(end_frame=entries[-1]['frame'], end_seq=entries[-1]['seq'], ended_by='capture_end')
        summary['segments'].append(current[index])
        summary['advance_histogram'] = histogram(counters[index])
    for camera in cameras.values():
        camera['progress_writers'] = histogram(camera['progress_writers'])
        camera['setter_callers'] = histogram(camera['setter_callers'])
    scripts, script_events = analyze_scripts(capture, ram, entries, spans)
    battle_stats, stat_events = analyze_battle_stats(ram, entries, spans)
    events.extend(script_events)
    events.extend(stat_events)
    events.sort(key=lambda event: event['seq'])
    return dict(schema=1, ram_sha256=hashlib.sha256(ram).hexdigest(),
                integrity=dict(writes=len(entries), first_frame=entries[0]['frame'],
                               last_frame=entries[-1]['frame'], recorder_totals_verified=has_totals),
                actors=summaries, cameras=list(cameras.values()), scripts=scripts, battle_stats=battle_stats,
                shared_step_histogram=histogram(shared_steps), events=events,
                caveats=['Guest frames and timeline entries are different units.',
                         'Snapshot ownership can become stale if objects are replaced during capture.',
                         'Clip IDs are resource-specific; events do not classify attacks universally.',
                         'A clip selection can replace an unfinished loop; capture end is not clip completion.',
                         'Consecutive sequences cannot detect an omitted tail without recorder totals.',
                         'Script commands are parsed requests, not proof of audible sound, rendered effects, or damage.',
                         'Consecutive command fetches at the same cursor are grouped as attempts, not unique executions.',
                         'Battle-local HP/MP updates are not final party-save commits or visible hit timestamps.',
                         'Trace and snapshot hashes identify inputs, not the running executable.',
                         'No accelerated runtime behavior or combat outcome is inferred.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, required=True)
    parser.add_argument('--ram', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must not already exist')
    trace_bytes = args.trace.read_bytes()
    result = analyze(json.loads(trace_bytes), args.ram.read_bytes())
    result['trace_sha256'] = hashlib.sha256(trace_bytes).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print(f"Validated {result['integrity']['writes']} writes; {len(result['actors'])} combatants")
    for actor in result['actors']:
        print(f"{actor['address']}: clips {actor['clip_sequence']}; "
              f"loops {sum(s['loops'] for s in actor['segments'])}; "
              f"completions {sum(s['completions'] for s in actor['segments'])}")


if __name__ == '__main__':
    main()
