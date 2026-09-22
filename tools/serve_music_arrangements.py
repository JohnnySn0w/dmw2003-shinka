"""Serve a local arrangement listening folder with audio seeking support."""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
import math
from pathlib import Path
import secrets
import threading
from urllib.parse import urlsplit

from serve_website import Handler


class Profiles:
    """Revision-checked atomic writes, isolated from the instrument notebook."""
    def __init__(self, directory, catalog):
        self.path = directory/'mix-adjustments.json'
        self.catalog = catalog
        self.lock = threading.Lock()
        self.allowed = {f"{track['id']}/{palette}": {str(p['part']) for p in data['parts']}
                        for track in catalog['tracks'] for palette, data in track['palettes'].items()}
        self.state = dict(identity=catalog['identity'], revision=0, values={})
        if self.path.exists():
            self.state = json.loads(self.path.read_text(encoding='utf-8'))
            if self.state['identity'] != catalog['identity']:
                raise ValueError('Saved adjustments belong to a different balance catalog')

    def save(self, request):
        with self.lock:
            if request.get('identity') != self.catalog['identity']:
                raise ValueError('Different balance catalog; reload before editing')
            if request.get('revision') != self.state['revision']:
                raise FileExistsError('Adjustments changed elsewhere; reload before editing')
            key, values = request.get('key'), request.get('values')
            if key not in self.allowed or not isinstance(values, dict) or set(values) != self.allowed[key]:
                raise ValueError('Unknown track, palette or parts')
            for controls in values.values():
                if not isinstance(controls, dict) or set(controls) != {'gain', 'warmth', 'presence'}:
                    raise ValueError('Expected volume, warmth and presence controls')
                for control, value in controls.items():
                    limit = 12 if control == 'gain' else 6
                    if (type(value) not in (float, int) or not math.isfinite(value) or abs(value) > limit):
                        raise ValueError('Control outside supported range')
            next_state = dict(identity=self.catalog['identity'], revision=self.state['revision']+1,
                              values={**self.state['values'], key: values})
            temporary = self.path.with_suffix('.json.tmp')
            temporary.write_text(json.dumps(next_state, indent=2)+'\n', encoding='utf-8')
            temporary.replace(self.path)
            self.state = next_state
            return next_state


class MixerHandler(Handler):
    def json_response(self, data, status=200):
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/':
            page = (Path(self.directory)/'index.html').read_text(encoding='utf-8')
            page = page.replace('<body>', '<body><p><a href="/mixer">Open the mix desk: balanced previews and instrument controls →</a></p>', 1)
            payload = page.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if path == '/api/mixer':
            if self.headers.get('Host') != self.server.expected_host:
                self.send_error(403)
                return
            with self.server.profiles.lock:
                self.json_response(dict(catalog=self.server.profiles.catalog,
                                        profile=self.server.profiles.state, token=self.server.token))
            return
        if path in ('/mixer', '/mixer.js', '/mixer.css'):
            name = 'index.html' if path == '/mixer' else path[1:]
            payload = (Path(__file__).parent/'music_mixer'/name).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', {'index.html': 'text/html; charset=utf-8',
                                             'mixer.js': 'text/javascript', 'mixer.css': 'text/css'}[name])
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path != '/api/profile':
            self.send_error(404)
            return
        if (self.headers.get('Host') != self.server.expected_host
                or self.headers.get('Origin') not in (None, 'http://'+self.server.expected_host)
                or self.headers.get('X-Mixer-Token') != self.server.token):
            self.send_error(403)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536:
                raise ValueError('Invalid request size')
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict):
                raise ValueError('Expected an object')
            self.json_response(self.server.profiles.save(request))
        except FileExistsError as error:
            self.json_response(dict(error=str(error)), 409)
        except (ValueError, TypeError) as error:
            self.json_response(dict(error=str(error)), 400)
        except OSError:
            self.json_response(dict(error='Could not save adjustments to disk; changes remain unsaved'), 500)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--port', type=int, default=62007)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not (directory/'arrangements.json').is_file():
        parser.error('Expected a rendered arrangement listening folder')
    balanced = directory/'balanced/catalog.json'
    handler = MixerHandler if balanced.exists() else Handler
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(handler, directory=str(directory)))
    if balanced.exists():
        server.profiles = Profiles(directory, json.loads(balanced.read_text(encoding='utf-8')))
        server.token = secrets.token_urlsafe(32)
        server.expected_host = f'127.0.0.1:{args.port}'
    print(f'Listening samples: http://127.0.0.1:{args.port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
