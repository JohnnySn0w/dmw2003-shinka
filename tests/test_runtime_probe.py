import io
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from runtime_probe import request


class RuntimeProbeTests(unittest.TestCase):
    def exchange(self, payload):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.makefile.return_value = io.BytesIO(payload)
        with patch('runtime_probe.socket.create_connection', return_value=connection):
            return request({'cmd': 'card_txn_dump'})

    def test_single_line(self):
        self.assertEqual(self.exchange(b'{"ok":true}\n'), {'ok': True})

    def test_multiline_transaction_response(self):
        data = b'{"ok":true,"entries":[\n {"sector":35},\n {"sector":36}\n]}\n'
        self.assertEqual(self.exchange(data)['entries'], [{'sector': 35}, {'sector': 36}])

    def test_incomplete_response(self):
        with self.assertRaisesRegex(ValueError, 'closed before'):
            self.exchange(b'{"entries":[\n')

    def test_delimiters_inside_escaped_string(self):
        import json
        expected = {'text': 'brackets } ] and quote " and slash \\', 'entries': [1, 2]}
        self.assertEqual(self.exchange((json.dumps(expected, indent=2) + '\n').encode()), expected)
