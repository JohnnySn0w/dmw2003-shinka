"""Enable or disable the experimental English evolution-chart menu shortcut."""
import argparse
import re
import tomllib
from pathlib import Path

PACKAGE = 'shinka.evolution-journal'


def select_journal(text, enabled):
    original = tomllib.loads(text) if text.strip() else {'format_version': 2}
    if original.get('format_version') != 2:
        raise ValueError('Unsupported mod-state version')
    kept = []
    for chunk in re.split(r'(?=^\[\[(?:package|feature)\]\]\s*$)', text, flags=re.M):
        parsed = tomllib.loads(chunk) if chunk.strip() else {}
        if parsed.get('package', [{}])[0].get('id') == PACKAGE:
            continue
        feature = parsed.get('feature', [{}])[0]
        if feature.get('package_id') == PACKAGE and feature.get('id') == 'menu-chart':
            continue
        kept.append(chunk)
    result = ''.join(kept).strip() or 'format_version = 2'
    result += f'''\n\n[[package]]
id = "{PACKAGE}"
version = "0.1.0"

[[feature]]
package_id = "{PACKAGE}"
id = "menu-chart"
enabled = {'true' if enabled else 'false'}
'''
    def unrelated(state):
        state = dict(state)
        state['package'] = [p for p in state.get('package', []) if p.get('id') != PACKAGE]
        state['feature'] = [f for f in state.get('feature', []) if not (
            f.get('package_id') == PACKAGE and f.get('id') == 'menu-chart')]
        return state
    if unrelated(original) != unrelated(tomllib.loads(result)):
        raise ValueError('Unrecognized mod-state layout; no state was changed')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--enable', action='store_true')
    mode.add_argument('--disable', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    mods = root / 'build-windows/Release/mods'
    state = mods / 'state.toml'
    original = state.read_text(encoding='utf-8') if state.exists() else ''
    content = select_journal(original, args.enable)
    package = mods / 'packages' / PACKAGE / '0.1.0'
    package.mkdir(parents=True, exist_ok=True)
    package.joinpath('manifest.toml').write_bytes(
        root.joinpath('mods/evolution-journal/manifest.toml').read_bytes())
    if state.exists():
        mods.joinpath('state.toml.journal-backup').write_text(original, encoding='utf-8')
    temporary = mods / 'state.toml.journal-tmp'
    temporary.write_text(content, encoding='utf-8')
    temporary.replace(state)
    print(f"Evolution chart shortcut {'enabled' if args.enable else 'disabled'}. Restart to apply.")


if __name__ == '__main__':
    main()
