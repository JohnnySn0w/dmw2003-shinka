"""Send one JSON command to the local PSXRecomp debug server.

Examples: runtime_probe.py '{"cmd":"ping"}'
          runtime_probe.py '{"cmd":"screenshot_file","path":"output/boot.png"}'
Use a dedicated --port when another runtime is running.
"""
import argparse
import json
import socket


def request(command, port=4380):
    with socket.create_connection(('127.0.0.1', port), timeout=10) as connection:
        command = dict(command)
        command.setdefault('id', 1)
        connection.sendall((json.dumps(command) + '\n').encode())
        with connection.makefile('rb') as stream:
            response = bytearray()
            limit = 16 * 1024 * 1024
            depth = 0
            in_string = escaped = started = False
            while len(response) < limit:
                line = stream.readline(limit - len(response))
                if not line:
                    raise ValueError('Debug server closed before a complete JSON response')
                response.extend(line)
                # Scan once instead of reparsing a growing transaction dump
                # after every line (quadratic work for large responses).
                for byte in line:
                    if in_string:
                        if escaped:
                            escaped = False
                        elif byte == 92:
                            escaped = True
                        elif byte == 34:
                            in_string = False
                    elif byte == 34:
                        in_string = True
                    elif byte in (123, 91):
                        started = True
                        depth += 1
                    elif byte in (125, 93):
                        depth -= 1
                if started and depth <= 0 and not in_string:
                    return json.loads(response)
            raise ValueError('Debug response exceeded 16 MiB')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', help='JSON command object')
    parser.add_argument('--port', type=int, default=4380)
    args = parser.parse_args()
    print(json.dumps(request(json.loads(args.command), args.port), indent=2))
