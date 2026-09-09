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
            response = stream.readline(16 * 1024 * 1024)
        return json.loads(response)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', help='JSON command object')
    parser.add_argument('--port', type=int, default=4380)
    args = parser.parse_args()
    print(json.dumps(request(json.loads(args.command), args.port), indent=2))
