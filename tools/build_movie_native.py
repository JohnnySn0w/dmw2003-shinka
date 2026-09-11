"""Compile the audited opening-movie routines from an owned STDWTITL.PRO.

All output contains game-derived code/data and must remain local and ignored.
Uses the pinned framework's emitter; does not copy disassembly reference code.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

MODULE_SHA256 = '2a8cf1a9eedbacc47434a1dfb1afd45fd711af4216bb8f2d8a1f0e82bd629639'
BASE = 0x80082cb0
END = BASE + 26048
ROOTS = [0x800872a4, 0x80087320, 0x8008780c]
EXPECTED_RANGES = {(0x872a4, 0x7c), (0x87320, 0x20), (0x874fc, 0x90),
                   (0x8758c, 0x8c), (0x87618, 0x94), (0x876ac, 0x94),
                   (0x87758, 0x7c), (0x8780c, 0x34c)}


def capture(module):
    if hashlib.sha256(module).hexdigest() != MODULE_SHA256:
        raise ValueError('Unsupported STDWTITL.PRO; extract it from the audited European disc')
    data = module[:END-BASE]
    return dict(schema='psxrecomp overlay capture v2', load_addr=hex(BASE),
                size=len(data), bytes_b64=base64.b64encode(data).decode(),
                executed_pcs=[hex(root) for root in ROOTS], dispatch_entry_pcs=[hex(root) for root in ROOTS],
                function_entry_pcs=[hex(root) for root in ROOTS], seeds=[hex(root) for root in ROOTS])


def validate_ranges(source):
    rows = re.findall(r'static const uint32_t psx_ov_static_ranges_\d+\[\] = \{ ([^}]+)', source)
    ranges = set()
    for row in rows:
        values = [int(v, 16) for v in re.findall(r'0x([0-9a-fA-F]+)u', row)]
        if len(values) != 2:
            raise ValueError('Review changed emitter range format')
        ranges.add(tuple(values))
    if ranges != EXPECTED_RANGES:
        raise ValueError('Generated movie coverage changed; review before enabling')


def build(args):
    module = args.module.read_bytes()
    recipe = capture(module)  # reject unsupported input before writing
    args.output.mkdir(parents=True, exist_ok=False)
    captures = args.output/'capture.json'
    captures.write_text(json.dumps([recipe])+'\n', encoding='utf-8')
    command = [sys.executable, str(args.framework/'tools/compile_overlays.py'),
               '--static', '--force', '--captures', str(captures),
               '--game-toml', str(args.game), '--recompiler', str(args.recompiler),
               '--runtime-include', str(args.framework/'runtime/include'),
               '--out-dir', str(args.output), '--cps', '--jobs', '1']
    environment = os.environ.copy()
    # Offline generation must use these audited bytes and the requested output,
    # even if launched from a shell that inherited runtime autocompile settings.
    for key in ('PSX_OVERLAY_CAPTURES', 'PSX_OVERLAY_CACHE_DIR', 'PSX_OVERLAY_FLAVOR'):
        environment.pop(key, None)
    with (args.output/'generate.log').open('w', encoding='utf-8') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, env=environment)
    source = args.output/'overlays_static.c'
    # The pinned Windows generator writes an ANSI banner; guard declarations
    # are ASCII. Latin-1 preserves every byte without changing generated code.
    validate_ranges(source.read_text(encoding='latin-1'))
    (args.output/'provenance.json').write_text(json.dumps(dict(
        module_sha256=MODULE_SHA256, roots=[hex(root) for root in ROOTS],
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        guarded_ranges=[dict(address=hex(a), size=n) for a, n in sorted(EXPECTED_RANGES)]
    ), indent=2)+'\n', encoding='utf-8')
    print(source.resolve())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module', type=Path, required=True)
    parser.add_argument('--framework', type=Path, required=True)
    parser.add_argument('--recompiler', type=Path, required=True)
    parser.add_argument('--game', type=Path, default=Path('game.toml'))
    parser.add_argument('--output', type=Path, required=True)
    build(parser.parse_args())
