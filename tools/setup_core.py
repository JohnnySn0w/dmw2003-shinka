"""First-run data handling. No discovery, downloads or writes happen on import."""
import configparser
import ctypes
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import tempfile
import zipfile

from save_profiles import describe_card, import_card

DISC_SHA1 = '457cb233349ba841e03b33d8060f8fbcadd45cb3'
TOOLCHAIN = dict(
    version='1.0.14', bytes=209497009,
    url='https://github.com/RetroPortingToolKit/RetroPorting-Toolchains/releases/download/v1.0.14/cmake-clang-v1-windows-x64.zip',
    sha256='28da9742385e7ff875b3d9311e8ed89dbdc84f27b6ecba2bc0d0acc11f6d2b4d')


class Cancelled(Exception):
    pass


def check_cancel(cancel):
    if cancel and cancel.is_set():
        raise Cancelled('Preparation cancelled. Your disc and existing saves were not changed.')


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_settings(root):
    path = Path(root) / 'launcher.json'
    if not path.exists():
        return {'schema': 1}
    settings = json.loads(path.read_text(encoding='utf-8'))
    if settings.get('schema') != 1:
        raise ValueError('Unsupported launcher settings. Existing data has been preserved.')
    return settings


def data_root():
    if os.name != 'nt':
        raise OSError('The Shinka launcher currently supports Windows only.')
    return Path(os.environ['LOCALAPPDATA']) / 'Shinka'


def hash_file(path, algorithm='sha256', cancel=None, progress=None):
    digest = hashlib.new(algorithm)
    with Path(path).open('rb') as stream:
        before = os.fstat(stream.fileno())
        total = 0
        while block := stream.read(1024 * 1024):
            check_cancel(cancel)
            digest.update(block)
            total += len(block)
            if progress:
                progress(total, before.st_size)
        after = os.fstat(stream.fileno())
    now = Path(path).stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
            now.st_size, now.st_mtime_ns, now.st_ino) or after.st_mtime_ns != before.st_mtime_ns:
        raise ValueError('The file changed while it was being checked. Close other programs and retry.')
    check_cancel(cancel)
    return digest.hexdigest()


def cue_bin(cue):
    """Accept the audited single-file/single-track layout, with explicit errors."""
    cue = Path(cue).resolve(strict=True)
    if cue.suffix.lower() != '.cue':
        raise ValueError('Choose the .cue file beside your disc .bin. CHD, ISO and ZIP are not supported yet.')
    with cue.open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536 or b'\0' in raw:
        raise ValueError('The CUE file is not a supported text cue sheet.')
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('cp1252')
    files = re.findall(r'^\s*FILE\s+"([^"]+)"\s+BINARY\s*$', text, re.M | re.I)
    tracks = re.findall(r'^\s*TRACK\s+(\d+)\s+(\S+)\s*$', text, re.M | re.I)
    if len(files) != 1 or len(re.findall(r'^\s*FILE\b', text, re.M | re.I)) != 1:
        raise ValueError('This version needs a single-BIN CUE dump; multiple BIN files are not supported.')
    if len(tracks) != 1 or int(tracks[0][0]) != 1 or tracks[0][1].upper() != 'MODE2/2352':
        raise ValueError('Expected one MODE2/2352 data track from Digimon World 2003 (Europe).')
    if not re.search(r'^\s*INDEX\s+01\s+00:00:00\s*$', text, re.M | re.I):
        raise ValueError('The CUE track must begin at INDEX 01 00:00:00.')
    ref = files[0]
    # Do not follow UNC/device paths or alternate data streams from a cue sheet.
    if ref.startswith(('\\\\', '//')) or ':' in ref or PureWindowsPath(ref).is_absolute():
        raise ValueError('Use a relative BIN filename in the CUE; network and device references are not supported.')
    binary = (cue.parent / ref.replace('\\', '/')).resolve()
    if not binary.is_file():
        raise FileNotFoundError(f'The BIN named by this CUE is missing:\n{binary}\nKeep the CUE and BIN together, or locate the correct CUE.')
    return cue, binary


def validate_disc(cue, cancel=None, progress=None):
    cue, binary = cue_bin(cue)
    if hash_file(binary, 'sha1', cancel, progress) != DISC_SHA1:
        raise ValueError('This dump does not match the supported European Digimon World 2003 disc (SLES-03936). Check the region and re-dump your disc if necessary. No files were changed.')
    stat = binary.stat()
    return dict(cue=str(cue), binary=str(binary), sha1=DISC_SHA1,
                size=stat.st_size, mtime_ns=stat.st_mtime_ns)


def remembered_disc_ok(disc):
    try:
        cue, binary = cue_bin(disc['cue'])
        stat = binary.stat()
        return (str(binary) == disc['binary'] and stat.st_size == disc['size']
                and stat.st_mtime_ns == disc['mtime_ns'] and disc['sha1'] == DISC_SHA1)
    except (OSError, ValueError, KeyError):
        return False


def emulator_running():
    """Best-effort Windows process-name check; the user also confirms closure."""
    import csv
    import subprocess
    result = subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/tasklist.exe'), '/FO', 'CSV', '/NH'],
                            capture_output=True, text=True, errors='replace', timeout=10,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise OSError('Could not check whether DuckStation is closed. Close it and retry.')
    return any(row and row[0].lower().startswith('duckstation') for row in csv.reader(result.stdout.splitlines()))


def activate(root, prepared, card=None, slot=1):
    """Commit only after a complete build and successful exclusive card import."""
    import shutil
    import uuid
    root = Path(root)
    settings = read_settings(root)
    runtime = Path(prepared['runtime'])
    if not (runtime/'dmw2003-shinka.exe').is_file():
        raise FileNotFoundError('The prepared game is missing. Run preparation again.')
    previous = Path(settings['runtime']) if settings.get('runtime') else None
    if previous and previous != runtime:
        for name in ('settings.toml', 'input.ini', 'keybinds.ini', 'mods/state.toml'):
            if (previous/name).is_file():
                target = runtime/name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(previous/name, target)
    profile = settings.get('profile')
    if card or not profile:
        new_profile = root/'saves'/('profile-' + uuid.uuid4().hex[:12])
        if card:
            import_card(card, new_profile, slot)
        else:
            new_profile.mkdir(parents=True, exist_ok=False)
        profile = str(new_profile)
    settings.update(schema=1, runtime=str(runtime), disc=prepared['disc'], profile=profile,
                    revision=prepared['revision'], sdk=prepared.get('sdk', settings.get('sdk', {})))
    atomic_json(root/'launcher.json', settings)
    return settings


def launch_command(settings):
    runtime = Path(settings['runtime'])
    if not remembered_disc_ok(settings['disc']):
        raise FileNotFoundError('The selected disc has moved or changed. Choose its CUE again to repair the path.')
    if not Path(settings['profile']).is_dir():
        raise FileNotFoundError('Your save-profile folder is missing. Restore it before playing; a blank replacement will not be created.')
    return [str(runtime/'dmw2003-shinka.exe'), '--game', str(runtime/'game.toml'),
            '--disc', settings['disc']['cue'], '--bios', str(runtime/'bios/openbios.bin'),
            '--memcard-dir', settings['profile'], '--no-launcher']


def default_duckstation_roots():
    """Bounded known folders, including Windows' redirected Documents folder."""
    roots = []
    if os.name == 'nt':
        buffer = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0:
            roots.append(Path(buffer.value) / 'DuckStation')
    for key in ('USERPROFILE', 'OneDrive', 'OneDriveConsumer', 'OneDriveCommercial'):
        if os.environ.get(key):
            roots.append(Path(os.environ[key]) / 'Documents' / 'DuckStation')
    for key in ('APPDATA', 'LOCALAPPDATA'):
        if os.environ.get(key):
            roots.append(Path(os.environ[key]) / 'DuckStation')
    return list(dict.fromkeys(roots))


def discover_cards(roots):
    """No recursion outside known folders or an explicitly configured path."""
    cards, errors, seen = [], [], set()
    for root in roots:
        root = Path(root).resolve()
        if not root.exists():
            continue
        folders = [root, root / 'memcards']
        ini = root / 'settings.ini'
        if ini.exists():
            try:
                if ini.stat().st_size > 1024 * 1024:
                    raise ValueError('Settings file is too large.')
                cfg = configparser.ConfigParser(interpolation=None, strict=False)
                cfg.read_string(ini.read_text(encoding='utf-8-sig'))
                configured = cfg.get('Folders', 'MemoryCards', fallback='').strip()
                if configured:
                    folders.append(root / configured)
                for key in ('Card1Path', 'Card2Path'):
                    configured = cfg.get('MemoryCards', key, fallback='').strip()
                    if configured:
                        folders.append((root / configured).parent)
            except (OSError, ValueError, configparser.Error) as exc:
                errors.append(f'{ini}: {exc}')
        for folder in folders:
            try:
                if not folder.exists():
                    continue
                for count, path in enumerate(folder.iterdir()):
                    if count >= 10000:
                        errors.append(f'{folder}: search stopped at 10,000 entries; choose a card file directly.')
                        break
                    if path.suffix.lower() not in ('.mcd', '.mcr') or not path.is_file():
                        continue
                    canonical = os.path.normcase(str(path.resolve()))
                    if canonical in seen:
                        continue
                    seen.add(canonical)
                    try:
                        cards.append(dict(**describe_card(path), modified=path.stat().st_mtime))
                    except (OSError, ValueError) as exc:
                        errors.append(f'{path}: {exc}')
            except OSError as exc:
                errors.append(f'{folder}: {exc}')
    return sorted(cards, key=lambda card: card['path'].casefold()), errors


def safe_extract(archive, destination, cancel=None, max_bytes=3 * 1024**3):
    """Reject traversal, Windows aliases and symlinks before writing any member."""
    destination = Path(destination).resolve()
    with zipfile.ZipFile(archive) as zipped:
        members = zipped.infolist()
        if len(members) > 100000 or sum(info.file_size for info in members) > max_bytes:
            raise ValueError('Archive exceeds its allowed expanded size.')
        names = set()
        for info in members:
            name = info.orig_filename
            parts = name.rstrip('/').split('/')
            if ('\\' in name or ':' in name or name.startswith('/')
                    or any(p in ('', '.', '..') or p.endswith((' ', '.')) or PureWindowsPath(p).is_reserved() for p in parts)
                    or (info.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError('Unsafe archive member: ' + name)
            key = name.rstrip('/').casefold()
            if key in names:
                raise ValueError('Duplicate archive member: ' + name)
            names.add(key)
        for info in members:
            check_cancel(cancel)
            target = destination / info.filename
            if not target.resolve().is_relative_to(destination):
                raise ValueError('Archive destination escapes its staging folder.')
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with zipped.open(info) as source, target.open('xb') as output:
                    while block := source.read(1024 * 1024):
                        check_cancel(cancel)
                        output.write(block)


class SetupLock:
    """OS-owned lock: a crash releases it; the file is not a stale lock marker."""
    def __init__(self, root):
        self.path = Path(root) / 'launcher.lock'
        self.stream = None

    def __enter__(self):
        import msvcrt
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open('a+b')
        self.stream.seek(0)
        if not self.stream.read(1):
            self.stream.write(b'0')
            self.stream.flush()
        self.stream.seek(0)
        try:
            msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            self.stream.close()
            raise RuntimeError('Shinka is already running. Close the other window first.') from None
        return self

    def __exit__(self, *args):
        import msvcrt
        self.stream.seek(0)
        msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
        self.stream.close()
