"""Build and select guarded EXP disc-read patches; never modify the input BIN."""
import argparse
import contextlib
import hashlib
import io
import json
import re
import struct
import tomllib
from pathlib import Path
from audit_disc import audit

DISC_SHA256 = 'fb70dc9a995aed628cf515cabc87c7b14e5142559076ec394dfe793ec3e26a04'
OVERLAY_SHA256 = 'c2e8845fccab5f2e852c1025fac2ee4f548c6136b1a1b47e6c838ce7eb5f1ef9'
PACKAGE = 'shinka.experience'
VERSION = '0.1.0'
TABLE = 0x3DD8
ROWS = 335


def exp_patches(data, lba, multiplier):
    if multiplier not in (1, 2, 3, 4):
        raise ValueError('EXP multiplier must be 1, 2, 3 or 4')
    if hashlib.sha256(data).hexdigest() != OVERLAY_SHA256:
        raise ValueError('Unsupported reward overlay')
    patches = []
    for row in range(ROWS):
        offset = TABLE + row * 12 + 4
        original = data[offset:offset + 4]
        value, = struct.unpack('<I', original)
        scaled = value * multiplier
        # The original two-participant arithmetic first multiplies by six.
        if scaled > 0x7FFFFFFF // 6:
            raise ValueError('EXP would overflow the original signed arithmetic')
        if scaled != value:
            patches.append((lba * 2048 + offset, original, struct.pack('<I', scaled)))
    return patches


def dv_patches(data, lba, multiplier):
    """Scale the final DV award argument after original rounding/minimum/caps."""
    if multiplier not in (1, 2, 3, 4):
        raise ValueError('DV multiplier must be 1, 2, 3 or 4')
    if hashlib.sha256(data).hexdigest() != OVERLAY_SHA256:
        raise ValueError('Unsupported reward overlay')
    offset = 0x1388
    original = data[offset:offset + 16]
    # lw v1,0x20(s0); nop; jalr v1; move a2,v0
    expected = struct.pack('<4I', 0x8E030020, 0, 0x0060F809, 0x00403021)
    if original != expected:
        raise ValueError('DV delivery call signature changed')
    if multiplier == 1:
        return []
    words = list(struct.unpack('<4I', original))
    if multiplier == 3:
        words[1] = 0x00023040  # sll a2,v0,1
        words[3] = 0x00C23021  # addu a2,a2,v0 (call delay slot)
    else:
        words[3] = 0x00023000 | ((1 if multiplier == 2 else 2) << 6)
    return [(lba * 2048 + offset, original, struct.pack('<4I', *words))]


def manifest(data, lba):
    text = f'''format_version = 5
id = "{PACKAGE}"
version = "{VERSION}"
name = "Shinka Experience"
channel = "developer"
description = "Independent normal battle and Digivolution EXP multipliers."
resolver = "declarative"

[[target]]
game_id = "SLES-03936"
disc_sha256 = "{DISC_SHA256}"

[[feature]]
id = "battle-exp"
name = "Battle EXP multiplier"
default_enabled = false

[[option]]
feature = "battle-exp"
id = "multiplier"
label = "EXP multiplier"
type = "integer"
min = 1
max = 4
step = 1
default = 1
'''
    text += '''
[[feature]]
id = "dv-exp"
name = "Digivolution EXP multiplier"
description = "Multiply the final DV award after original rounding and caps."
default_enabled = false

[[option]]
feature = "dv-exp"
id = "multiplier"
label = "DV EXP multiplier"
type = "integer"
min = 1
max = 4
step = 1
default = 1
'''
    for feature_id, generate in [('battle-exp', exp_patches), ('dv-exp', dv_patches)]:
        for factor in (2, 3, 4):
            for offset, expected, replacement in generate(data, lba, factor):
                text += f'''
[[patch]]
feature = "{feature_id}"
target = "disc_user"
offset = {offset}
expected = "{expected.hex(' ')}"
replace = "{replacement.hex(' ')}"
when = {{ multiplier = "{factor}" }}
'''
    return text


def select_feature(text, multiplier, feature_id='battle-exp'):
    """Preserve other packages/features verbatim, replacing only our records."""
    if feature_id not in ('battle-exp', 'dv-exp') or multiplier not in (1, 2, 3, 4):
        raise ValueError('Unsupported EXP feature or multiplier')
    parsed = tomllib.loads(text) if text.strip() else {'format_version': 2}
    if parsed.get('format_version') != 2:
        raise ValueError('Only mod state format 2 is supported; no state was changed')
    chunks = re.split(r'(?m)(?=^\[\[(?:package|feature)\]\]\s*$)', text)
    kept = []
    for chunk in chunks:
        record = tomllib.loads(chunk) if chunk.strip() else {}
        package = record.get('package', [{}])[0]
        feature = record.get('feature', [{}])[0]
        if package.get('id') == PACKAGE or (
                feature.get('package_id') == PACKAGE and feature.get('id') == feature_id):
            continue
        kept.append(chunk)
    result = ''.join(kept).strip() or 'format_version = 2'
    result += f'''

[[package]]
id = "{PACKAGE}"
version = "{VERSION}"

[[feature]]
package_id = "{PACKAGE}"
id = "{feature_id}"
enabled = {'true' if multiplier != 1 else 'false'}
[feature.values]
multiplier = "{multiplier}"
'''
    updated = tomllib.loads(result)
    # Fail closed if an unfamiliar state layout was disturbed by the edit.
    def unrelated(state):
        state = dict(state)
        state['package'] = [p for p in state.get('package', []) if p.get('id') != PACKAGE]
        state['feature'] = [f for f in state.get('feature', []) if not (
            f.get('package_id') == PACKAGE and f.get('id') == feature_id)]
        return state
    if unrelated(parsed) != unrelated(updated):
        raise ValueError('Unrecognized mod state layout; no state was changed')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disc-bin', type=Path, required=True)
    parser.add_argument('--multiplier', type=int, choices=(1, 2, 3, 4))
    parser.add_argument('--dv-multiplier', type=int, choices=(1, 2, 3, 4))
    args = parser.parse_args()
    if args.multiplier is None and args.dv_multiplier is None:
        parser.error('Specify --multiplier and/or --dv-multiplier')
    root = Path(__file__).resolve().parents[1]
    destination = root / 'output/exp-audit'
    with contextlib.redirect_stdout(io.StringIO()):
        audit(args.disc_bin, destination, selected=('STFGTREP.PRO',))
    report = json.loads((destination / 'disc-audit.json').read_text())
    if report['hashes']['sha256'] != DISC_SHA256:
        raise ValueError('Unsupported disc; mod configuration was not changed')
    entry, = [e for c in report['catalog'] for e in c['entries']
              if e['name'] == 'STFGTREP.PRO;1']
    data = (destination / 'STFGTREP.PRO').read_bytes()
    content = manifest(data, entry['lba'])
    generated = root / 'output/exp-mod'
    generated.mkdir(parents=True, exist_ok=True)
    (generated / 'manifest.toml').write_text(content, encoding='utf-8')
    mods = root / 'build-windows/Release/mods'
    state = mods / 'state.toml'
    previous = state.read_text(encoding='utf-8') if state.exists() else ''
    selected = previous
    for feature_id, factor in [('battle-exp', args.multiplier), ('dv-exp', args.dv_multiplier)]:
        if factor is not None:
            selected = select_feature(selected, factor, feature_id)
    package = mods / 'packages' / PACKAGE / VERSION
    package.mkdir(parents=True, exist_ok=True)
    (package / 'manifest.toml').write_text(content, encoding='utf-8')
    if state.exists():
        (mods / 'state.toml.shinka-backup').write_text(previous, encoding='utf-8')
    temporary = mods / 'state.toml.shinka-tmp'
    temporary.write_text(selected, encoding='utf-8')
    temporary.replace(state)
    if args.multiplier is not None:
        print(f'Selected {args.multiplier}x base battle EXP.')
    if args.dv_multiplier is not None:
        print(f'Selected {args.dv_multiplier}x final DV EXP.')
    print('Restart to apply. The stock disc is unchanged; 1x disables each feature independently.')


if __name__ == '__main__':
    main()
