"""Preview website/dist on localhost, including byte ranges for video seeking."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re


def byte_range(header, size):
    match = re.fullmatch(r'bytes=(\d*)-(\d*)', header)
    if not match or not size or not any(match.groups()):
        raise ValueError('Invalid byte range')
    left, right = match.groups()
    if not left:
        length = int(right)
        if not length:
            raise ValueError('Empty suffix')
        return max(0, size-length), size-1
    start = int(left)
    end = min(int(right), size-1) if right else size-1
    if start >= size or start > end:
        raise ValueError('Unsatisfiable byte range')
    return start, end


class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        self.remaining = None
        path = Path(self.translate_path(self.path))
        if 'Range' not in self.headers or not path.is_file():
            return super().send_head()
        try:
            stream = path.open('rb')
        except OSError:
            self.send_error(404)
            return None
        size = path.stat().st_size
        try:
            start, end = byte_range(self.headers['Range'], size)
        except ValueError:
            stream.close()
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return None
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(str(path)))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(end-start+1))
        self.end_headers()
        stream.seek(start)
        self.remaining = end-start+1
        return stream

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def copyfile(self, source, outputfile):
        try:
            if self.remaining is None:
                return super().copyfile(source, outputfile)
            while self.remaining:
                block = source.read(min(65536, self.remaining))
                if not block:
                    break
                outputfile.write(block)
                self.remaining -= len(block)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # Switching clips may cancel an in-flight media response.


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=4173)
    args = parser.parse_args()
    directory = Path(__file__).resolve().parents[1] / 'website/dist'
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, directory=str(directory)))
    print(f'Shinka preview: http://127.0.0.1:{args.port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
