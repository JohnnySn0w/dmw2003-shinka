"""Generate guarded, game-owned copies of CPS shards; never edit upstream output."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

ENTRIES = {
    '00': [('8001270C', 'shinka_journal_quick_menu'), ('800121B4', 'shinka_menu_construct')],
    '01': [('80014504', 'shinka_menu_allocate')],
    '02': [('80016B88', 'shinka_journal_transition')],
    '03': [('800194E8', 'shinka_menu_text')],
    '05': [('8001ED6C', 'shinka_menu_background')],
}


def shard(code, number):
    declarations = ['extern uint32_t shinka_menu_slot(uint32_t, uint32_t);']
    for address, callback in ENTRIES[number]:
        needle = f'debug_server_log_call_entry(0x{address}u);'
        if code.count(needle) != 1:
            raise ValueError(f'Review entry {address}: expected one real CPS entry')
        code = code.replace(needle, needle + f'\n    {callback}(cpu);')
        declarations.append(f'extern void {callback}(CPUState*);')
    if number == '01':
        needle = '    PGXP_STORE(0xAC800018u, _pgxa, cpu->gpr[0]); }  /* 0x800142B8: 0xAC800018 */'
        if code.count(needle) != 1:
            raise ValueError('Review resident task-advance substate reset')
        code = code.replace(needle, needle + '\n    shinka_menu_task_ready(cpu);')
        declarations.append('extern void shinka_menu_task_ready(CPUState*);')
    # Slots 6 and 7 are appended after the existing cursor and party widgets.
    # Change only the address expression, including PGXP's matching address.
    sites = [('80012230', 18, 22), ('80012920', 6, 17), ('80012DBC', 2, 17)]
    for address, reg, owner in sites:
        expected = 1 if number == '00' or (number == '01' and address != '80012230') else 0
        pattern = r'    \{ uint32_t _pgxa = [^\n]*\n[^\n]* /\* 0x' + address + r': [^\n]*'
        matches = list(re.finditer(pattern, code))
        if len(matches) != expected:
            raise ValueError(f'Review row access {address} in shard {number}')
        if matches:
            old = matches[0].group()
            expression = f'cpu->gpr[{reg}] + 12'
            if old.count(expression) != 2:
                raise ValueError(f'Review generated memory access {address}')
            new = old.replace(expression, f'shinka_menu_slot(cpu->gpr[{owner}], {expression})')
            code = code.replace(old, new)
    return code.replace('#include "SLES_039.36_decls.h"',
                        '#include "SLES_039.36_decls.h"\n' + '\n'.join(declarations))


def reward_header(data):
    if hashlib.sha256(data).hexdigest() != 'c2e8845fccab5f2e852c1025fac2ee4f548c6136b1a1b47e6c838ce7eb5f1ef9':
        raise ValueError('Unsupported reward overlay')
    # Local build artifact only. Used to reject unrelated/revised RAM overlays.
    words = struct.unpack(f'<{len(data)//4}I', data)
    return '/* Generated from the owner\'s disc. Do not distribute. */\nstatic const uint32_t reward_stock[] = {\n' + ',\n'.join(
        ','.join(f'0x{w:08x}u' for w in words[i:i+8]) for i in range(0, len(words), 8)) + '\n};\n'


def write_changed(path, content):
    if not path.exists() or path.read_text() != content:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('reward', type=Path)
    parser.add_argument('--manifest-output', type=Path)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    for number in ENTRIES:
        source = args.source / f'SLES_039.36_full_{number}.c'
        write_changed(args.destination / f'journal_{number}.c', shard(source.read_text(), number))
    data = args.reward.read_bytes()
    write_changed(args.destination / 'reward_stock.h', reward_header(data))
    if args.manifest_output:
        from configure_exp import manifest, DISC_SHA256
        report = json.loads(args.reward.with_name('disc-audit.json').read_text())
        if report['hashes']['sha256'] != DISC_SHA256:
            raise ValueError('Unsupported disc audit for reward manifest')
        entry, = [e for c in report['catalog'] for e in c['entries'] if e['name'] == 'STFGTREP.PRO;1']
        write_changed(args.manifest_output, manifest(data, entry['lba']))
