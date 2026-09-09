"""Synthetic image checks; no retail game data required."""
import contextlib
import importlib.util
import io
import json
import struct
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('audit_disc', Path(__file__).parents[1] / 'tools/audit_disc.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def record(name, lba, size, flags=0):
    data = bytearray(33 + len(name) + (len(name) % 2 == 0))
    data[0] = len(data)
    struct.pack_into('<I', data, 2, lba)
    struct.pack_into('<I', data, 10, size)
    data[25], data[32] = flags, len(name)
    data[33:33 + len(name)] = name
    return data


def fixture(path):
    sectors = [bytearray(2048) for _ in range(25)]
    pvd = sectors[16]
    pvd[:7] = b'\x01CD001\x01'
    pvd[40:72] = b'TEST'.ljust(32)
    struct.pack_into('<I', pvd, 132, 10)
    struct.pack_into('<I', pvd, 140, 18)
    struct.pack_into('<I', pvd, 158, 19)
    struct.pack_into('<I', pvd, 166, 2048)
    sectors[18][:10] = b'\x01\x00\x13\x00\x00\x00\x01\x00\x00\x00'
    root = record(b'\x00', 19, 2048, 2) + record(b'SLES_039.36;1', 20, 2048)
    sectors[19][:len(root)] = root
    sectors[20][:8] = b'PS-X EXE'
    with path.open('wb') as stream:
        for payload in sectors:
            header = b'\x00' + b'\xff' * 10 + b'\x00' + b'\x00\x00\x00\x02' + bytes(8)
            stream.write(header + payload + bytes(280))


class DiscAuditTests(unittest.TestCase):
    def test_extract_and_preserve_source(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'disc.bin'
            fixture(path)
            before = path.read_bytes()
            output = Path(temp) / 'out'
            with contextlib.redirect_stdout(io.StringIO()):
                module.audit(path, output, True)
            report = json.loads((output / 'disc-audit.json').read_text())
            self.assertEqual(report['volume'], 'TEST')
            self.assertEqual(len(report['catalog']), 1)
            self.assertEqual((output / 'SLES_039.36').read_bytes()[:8], b'PS-X EXE')
            self.assertEqual(path.read_bytes(), before)

    def test_reject_truncated_image(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bad.bin'
            path.write_bytes(b'bad')
            with self.assertRaises(ValueError):
                module.audit(path, Path(temp) / 'out')

    def test_reject_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'disc.bin'
            fixture(path)
            with self.assertRaises(ValueError):
                module.audit(path, Path(temp) / 'out', selected=['../escape'])
            self.assertFalse((Path(temp) / 'out').exists())


if __name__ == '__main__':
    unittest.main()
