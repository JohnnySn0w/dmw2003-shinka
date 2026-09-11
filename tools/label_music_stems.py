"""Local instrument-labeling workspace for split_music_ost and native captures.

Labels live in a separate atomic JSON file, keyed by source identity and family,
not part numbers or browser storage. Only explicitly indexed audio is served.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import threading
from urllib.parse import urlsplit


UI = Path(__file__).with_name('music_labeler')


def family_identity(manifest, part):
    return dict(bank=manifest['bank'], sequence=manifest['sequence'],
                source_sha256=manifest['source_sha256'],
                programs=sorted(part['programs']), samples=sorted(part['samples']))


def identity_key(identity):
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


def contained_file(root, name):
    path = (root/name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Missing audio file or path outside capture directory')
    return path


def load_catalog(library, native):
    report = json.loads((library/'batch.json').read_text(encoding='utf-8'))
    tracks, parts, audio, seeds = [], {}, {}, {}
    known_tracks = {t['id'] for t in report['tracks']}
    if set(native)-known_tracks:
        raise ValueError('Native capture names an absent library track')
    for row in report['tracks']:
        m = row['manifest']
        context = m.get('context') or {}
        track = dict(id=row['id'], title=context.get('title', row['id']),
                     scene=context.get('scene', 'Scene not yet identified.'),
                     scene_verified=context.get('runtime_scene_verified', False), parts=[])
        original = None
        labels = {}
        if row['id'] in native:
            folder = native[row['id']]
            original = json.loads((folder/'stems.json').read_text(encoding='utf-8'))
            if original['bank'] != m['bank'] or original['source_sha256'] != m['source_sha256']:
                raise ValueError('Native capture identity differs from library track')
            if (folder/'identifications.json').exists():
                imported = json.loads((folder/'identifications.json').read_text(encoding='utf-8-sig'))
                if imported['bank'] != m['bank'] or imported['source_sha256'] != m['source_sha256']:
                    raise ValueError('Identification source identity differs from native capture')
                labels = imported['parts']
        for p in m['parts']:
            identity = family_identity(m, p)
            key = identity_key(identity)
            if key in parts:
                raise ValueError('Duplicate family identity')
            part = dict(key=key, number=p['part'], identity=identity, sources=['offline'])
            for kind, field in [('short', 'audition'), ('full', 'file')]:
                audio[key, 'offline', kind] = contained_file(library/row['id'], p[field])
            if original:
                matches = [np for np in original['parts']
                           if sorted(np['programs']) == identity['programs']
                           and sorted(np['samples']) == identity['samples']]
                if len(matches) > 1:
                    raise ValueError('Ambiguous native family')
                if matches:
                    np = matches[0]
                    part['sources'].insert(0, 'native')
                    for kind, field in [('short', 'audition'), ('full', 'file')]:
                        audio[key, 'native', kind] = contained_file(native[row['id']], np[field])
                    old = labels.get(str(np['part']))
                    if old:
                        if sorted(old['programs']) != identity['programs'] or sorted(old['samples']) != identity['samples']:
                            raise ValueError('Imported label family differs from native capture')
                        seeds[key] = dict(instrument=old['instrument'], notes=old.get('user_description', ''),
                                          confidence='tentative' if 'uncertain' in old.get('status', '') else 'confident',
                                          audio_source='native')
            parts[key] = part
            track['parts'].append(part)
        tracks.append(track)
    return tracks, parts, audio, seeds


class LabelStore:
    def __init__(self, path, parts, seeds):
        self.path, self.parts = path, parts
        self.lock = threading.Lock()
        self.document = json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(schema_version=1, labels={})
        if self.document.get('schema_version') != 1 or not isinstance(self.document.get('labels'), dict):
            raise ValueError('Unsupported label file')
        for key, label in self.document['labels'].items():
            if identity_key(label['identity']) != key:
                raise ValueError('Stored label identity mismatch')
        for key, seed in seeds.items():
            if key not in self.document['labels']:
                self.save(dict(key=key, revision=0, **seed))

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps(self.document))

    def save(self, payload):
        key = payload.get('key')
        if key not in self.parts:
            raise ValueError('Unknown instrument family')
        for field, limit in [('instrument', 160), ('notes', 3000)]:
            if not isinstance(payload.get(field), str) or len(payload[field]) > limit:
                raise ValueError(f'Invalid {field}')
        if payload.get('confidence') not in ('confident', 'tentative', 'unknown'):
            raise ValueError('Invalid confidence')
        if payload.get('audio_source') not in self.parts[key]['sources']:
            raise ValueError('Unknown audio source')
        if type(payload.get('revision')) is not int:
            raise ValueError('Missing label revision')
        with self.lock:
            previous = self.document['labels'].get(key, {})
            if payload['revision'] != previous.get('revision', 0):
                raise FileExistsError('This label changed in another tab. Reload before editing it.')
            entry = dict(identity=self.parts[key]['identity'], instrument=payload['instrument'].strip(),
                         notes=payload['notes'].strip(), confidence=payload['confidence'],
                         audio_source=payload['audio_source'], revision=payload['revision']+1,
                         updated_at=datetime.now(timezone.utc).isoformat())
            # Publish the new in-memory document only after the atomic file write.
            document = dict(self.document, labels=dict(self.document['labels'], **{key: entry}))
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix(self.path.suffix+'.tmp')
            temp.write_text(json.dumps(document, indent=2)+'\n', encoding='utf-8')
            temp.replace(self.path)
            self.document = document
            return entry


def handler_for(tracks, audio, store, token):
    class Handler(BaseHTTPRequestHandler):
        def json_response(self, code, data):
            content = json.dumps(data).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(content)

        def allowed(self):
            expected = f'127.0.0.1:{self.server.server_port}'
            return self.headers.get('Host') == expected

        def do_GET(self):
            if not self.allowed():
                self.send_error(403)
                return
            path = urlsplit(self.path).path
            if path == '/api/catalog':
                self.json_response(200, dict(tracks=tracks, labels=store.snapshot()['labels'], token=token))
                return
            if path == '/api/labels':
                self.json_response(200, store.snapshot())
                return
            static = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
                      '/style.css': ('style.css', 'text/css')}
            if path in static:
                name, mime = static[path]
                content = (UI/name).read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', mime+'; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(content)
                return
            match = re.fullmatch(r'/audio/([a-f0-9]{64})/(native|offline)/(short|full)', path)
            if match and match.groups() in audio:
                self.serve_audio(audio[match.groups()])
                return
            self.send_error(404)

        def serve_audio(self, path):
            size = path.stat().st_size
            start, end = 0, size-1
            requested = self.headers.get('Range')
            if requested:
                match = re.fullmatch(r'bytes=(\d+)-(\d*)', requested)
                if not match:
                    self.send_error(416)
                    return
                start = int(match[1])
                end = min(int(match[2]), size-1) if match[2] else size-1
                if not 0 <= start <= end < size:
                    self.send_error(416)
                    return
            self.send_response(206 if requested else 200)
            self.send_header('Content-Type', 'audio/wav')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(end-start+1))
            if requested:
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            self.end_headers()
            try:
                with path.open('rb') as f:
                    f.seek(start)
                    remaining = end-start+1
                    while remaining:
                        block = f.read(min(65536, remaining))
                        if not block:
                            break
                        self.wfile.write(block)
                        remaining -= len(block)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass  # normal when the listener stops or seeks

        def do_POST(self):
            origin = f'http://127.0.0.1:{self.server.server_port}'
            if (not self.allowed() or self.headers.get('Origin') not in (None, origin)
                    or self.headers.get('X-Label-Token') != token):
                self.send_error(403)
                return
            if self.path != '/api/labels':
                self.send_error(404)
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 16384:
                    raise ValueError('Invalid request size')
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError('Expected a label object')
                self.json_response(200, store.save(payload))
            except FileExistsError as exc:
                self.json_response(409, dict(error=str(exc)))
            except (ValueError, TypeError) as exc:
                self.json_response(400, dict(error=str(exc)))
            except OSError:
                self.json_response(500, dict(error='Could not save to disk. Your edits are still in the form; try again.'))
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--labels', type=Path, default=Path('output/music-instrument-labels.json'))
    parser.add_argument('--native', action='append', default=[], metavar='TRACK=DIRECTORY')
    parser.add_argument('--port', type=int, default=4387)
    args = parser.parse_args()
    native = {}
    for spec in args.native:
        name, directory = spec.split('=', 1)
        native[name] = Path(directory)
    tracks, parts, audio, seeds = load_catalog(args.library, native)
    store = LabelStore(args.labels, parts, seeds)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(tracks, audio, store, secrets.token_urlsafe(32)))
    print(f'Instrument labels: http://127.0.0.1:{server.server_port}/', flush=True)
    print(f'Labels saved to {args.labels.resolve()}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
