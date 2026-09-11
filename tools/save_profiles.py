"""Locate memory cards and import a raw card into a new Shinka save profile."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

CARD_BYTES = 128 * 1024
MANIFEST = 'shinka-card-import.json'
ROOT = Path(__file__).resolve().parents[1]


def read_card(path):
    """Read a bounded raw-card snapshot; this is not a full save-integrity check."""
    with Path(path).open('rb') as stream:
        data = stream.read(CARD_BYTES + 1)
    if len(data) != CARD_BYTES or data[:2] != b'MC':
        raise ValueError('Expected a raw 128 KiB memory card with an MC header, '
                         'not an emulator savestate or individual exported save.')
    return data


def describe_card(path):
    path = Path(path).resolve()
    data = read_card(path)
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def import_card(source, destination, slot=1):
    if slot not in (1, 2):
        raise ValueError('Card slot must be 1 or 2.')
    source = Path(source).resolve(strict=True)
    # Do not follow an existing destination symlink, even if its target is absent.
    destination = Path(os.path.abspath(destination))
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Choose a new profile directory; existing profiles are never replaced.')
    data = read_card(source)
    digest = hashlib.sha256(data).hexdigest()
    record = dict(schema=1, imported_at=datetime.now(timezone.utc).isoformat(),
                  source=str(source), card=f'card{slot}.mcd', bytes=len(data), sha256=digest)
    destination.mkdir(parents=True, exist_ok=False)
    created = []
    try:
        # Exclusive creation also protects a file created by another process.
        for filename, payload in ((record['card'], data),
                                  (MANIFEST, (json.dumps(record, indent=2) + '\n').encode('utf-8'))):
            path = destination / filename
            with path.open('xb') as stream:
                created.append(path)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        if read_card(destination / record['card']) != data:
            raise OSError('Imported card verification failed.')
        if read_card(source) != data:
            raise OSError('Source card changed during import. Close the emulator and try again.')
    except BaseException:
        # Only remove files created by this call, never an existing profile or
        # unrelated files. rmdir deliberately fails if someone else added files.
        for path in reversed(created):
            try:
                path.unlink()
            except OSError:
                pass
        try:
            destination.rmdir()
        except OSError:
            pass
        raise
    return dict(profile=str(destination.resolve()), **record)


def find_profiles(root, depth=3):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Profile search root must be a directory.')
    if not 0 <= depth <= 8:
        raise ValueError('Search depth must be between 0 and 8.')
    profiles = []
    def walk_error(error):
        raise error
    for directory, children, files in os.walk(root, followlinks=False, onerror=walk_error):
        current = Path(directory)
        children[:] = sorted(name for name in children
                             if not (current / name).is_symlink() and not name.startswith('.'))
        if len(current.relative_to(root).parts) >= depth:
            children.clear()
        cards = []
        for name in ('card1.mcd', 'card2.mcd'):
            if name not in files:
                continue
            try:
                card = dict(name=name, status='raw card', **describe_card(current / name))
            except (OSError, ValueError) as error:
                card = dict(name=name, status='unreadable or unsupported', error=str(error))
            cards.append(card)
        if cards:
            profiles.append(dict(profile=str(current), cards=cards))
    return profiles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    inspect = commands.add_parser('inspect', help='Check a raw card and show its fingerprint')
    inspect.add_argument('card', type=Path)
    inspect.add_argument('--json', action='store_true')
    listing = commands.add_parser('list', help='Find card1/card2 files in local save profiles')
    listing.add_argument('--root', type=Path, default=ROOT / 'output')
    listing.add_argument('--depth', type=int, default=3, choices=range(9))
    listing.add_argument('--json', action='store_true')
    importing = commands.add_parser('import-card', help='Copy a card into a NEW save profile')
    importing.add_argument('source', type=Path)
    importing.add_argument('destination', type=Path)
    importing.add_argument('--slot', type=int, choices=(1, 2), default=1)
    importing.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'inspect':
            result = describe_card(args.card)
            message = f"{result['path']}\nRaw memory card: 128 KiB\nSHA-256: {result['sha256']}"
        elif args.command == 'list':
            result = find_profiles(args.root, args.depth)
            message = '\n\n'.join(item['profile'] + '\n' + '\n'.join(
                f"  {card['name']}: {card['status']}" for card in item['cards']) for item in result)
            if not message:
                message = 'No card1.mcd/card2.mcd files found in this search range.'
        else:
            result = import_card(args.source, args.destination, args.slot)
            message = (f"Imported {result['card']} into:\n{result['profile']}\n"
                       'Use this directory with launch_windows.ps1 -SaveDirectory, '
                       'then load the card through Continue in the game.')
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(result, indent=2) if args.json else message)


if __name__ == '__main__':
    main()
