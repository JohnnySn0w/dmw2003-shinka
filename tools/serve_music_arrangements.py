"""Serve a local arrangement listening folder with audio seeking support."""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

from serve_website import Handler


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--port', type=int, default=62007)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not (directory/'arrangements.json').is_file():
        parser.error('Expected a rendered arrangement listening folder')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, directory=str(directory)))
    print(f'Listening samples: http://127.0.0.1:{args.port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
