"""Sample live card transactions, guest frames and UI screenshots without input.

Run from the repository root; output must be a new directory under output/.
This is diagnostic sampling, not a precise profiler or a save-completion oracle.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
from runtime_probe import request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--card', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=20)
    parser.add_argument('--port', type=int, default=4380)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    destination = args.output.resolve()
    if not destination.is_relative_to(root / 'output'):
        parser.error('--output must be inside the repository output directory')
    if not 0 < args.seconds <= 60:
        parser.error('--seconds must be between 0 and 60')
    destination.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    index = 0
    with (destination / 'samples.jsonl').open('w', encoding='utf-8') as log:
        while time.monotonic() - started < args.seconds:
            began = time.monotonic()
            registers = request({'cmd': 'get_registers'}, args.port)
            # Keep enough history to see real slot-0 writes even when the last
            # transaction is background polling of the unused second slot.
            transactions = request({'cmd': 'card_txn_dump', 'count': 64, 'slot': 0}, args.port)
            data = args.card.read_bytes()
            sample = dict(t=began-started, frame=registers.get('frame'),
                          total_closed=transactions.get('total_closed'),
                          open=transactions.get('open'),
                          card_sha256=hashlib.sha256(data).hexdigest(),
                          transactions=[{k: v for k, v in e.items() if k not in ('tx', 'rx')}
                                        for e in transactions.get('entries', [])])
            if index % 2 == 0:
                shot = destination / f'{index:04d}.png'
                sample['screenshot'] = request({'cmd': 'screenshot_file', 'path': str(shot)}, args.port)
            sample['sample_ms'] = (time.monotonic() - began) * 1000
            log.write(json.dumps(sample) + '\n')
            log.flush()
            index += 1
            time.sleep(max(0, 0.5 - (time.monotonic() - began)))
    print(f'Recorded {index} samples in {destination}')


if __name__ == '__main__':
    main()
