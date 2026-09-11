import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import save_profiles as saves


class SaveProfilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = b'MC' + bytes(range(256)) * 511 + bytes(254)
        self.source = self.root / 'DuckStation card.mcd'
        self.source.write_bytes(self.data)
        self.destination = self.root / 'new profile'

    def test_import_preserves_source_and_records_exact_copy(self):
        result = saves.import_card(self.source, self.destination)
        self.assertEqual(self.source.read_bytes(), self.data)
        self.assertEqual((self.destination / 'card1.mcd').read_bytes(), self.data)
        self.assertEqual(result['sha256'], hashlib.sha256(self.data).hexdigest())
        record = json.loads((self.destination / saves.MANIFEST).read_text())
        self.assertEqual(record['sha256'], result['sha256'])
        self.assertEqual(record['source'], str(self.source.resolve()))

    def test_existing_profile_including_empty_directory_is_untouched(self):
        self.destination.mkdir()
        for with_card in (False, True):
            if with_card:
                (self.destination / 'card1.mcd').write_bytes(b'keep this')
            with self.assertRaises(FileExistsError):
                saves.import_card(self.source, self.destination)
        self.assertEqual((self.destination / 'card1.mcd').read_bytes(), b'keep this')

    def test_invalid_header_size_and_state_rejected_before_creating_profile(self):
        for payload in (b'PST\0', b'MC', b'MC' + bytes(saves.CARD_BYTES),
                        b'NO' + bytes(saves.CARD_BYTES - 2)):
            self.source.write_bytes(payload)
            with self.assertRaises(ValueError):
                saves.import_card(self.source, self.destination)
            self.assertFalse(self.destination.exists())

    def test_slot_two_import_and_slot_bounds(self):
        with self.assertRaises(ValueError):
            saves.import_card(self.source, self.destination, slot=3)
        saves.import_card(self.source, self.destination, slot=2)
        self.assertEqual((self.destination / 'card2.mcd').read_bytes(), self.data)
        self.assertFalse((self.destination / 'card1.mcd').exists())

    def test_changing_source_rolls_back_only_the_new_copy(self):
        original = saves.read_card
        calls = 0
        def changing(path):
            nonlocal calls
            calls += 1
            if calls == 3:
                return self.data[:-1] + b'X'
            return original(path)
        with patch.object(saves, 'read_card', side_effect=changing):
            with self.assertRaisesRegex(OSError, 'changed during import'):
                saves.import_card(self.source, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.source.read_bytes(), self.data)

    def test_write_failure_leaves_no_partial_profile(self):
        for fail_after in (0, 1):
            with self.subTest(fail_after=fail_after):
                with patch.object(saves.os, 'fsync', side_effect=[None] * fail_after + [OSError('disk full')]):
                    with self.assertRaisesRegex(OSError, 'disk full'):
                        saves.import_card(self.source, self.destination)
                self.assertFalse(self.destination.exists())
                self.assertEqual(self.source.read_bytes(), self.data)

    def test_cleanup_preserves_unrelated_file_created_during_import(self):
        def failing_sync(_descriptor):
            (self.destination / 'unrelated.txt').write_text('keep')
            raise OSError('disk full')
        with patch.object(saves.os, 'fsync', side_effect=failing_sync):
            with self.assertRaises(OSError):
                saves.import_card(self.source, self.destination)
        self.assertEqual(list(self.destination.iterdir()), [self.destination / 'unrelated.txt'])

    def test_discovery_depth_and_invalid_cards(self):
        profile = self.root / 'release' / 'saves'
        profile.mkdir(parents=True)
        (profile / 'card1.mcd').write_bytes(self.data)
        (profile / 'card2.mcd').write_bytes(b'broken')
        self.assertEqual(saves.find_profiles(self.root, depth=1), [])
        result = saves.find_profiles(self.root, depth=2)
        self.assertEqual(len(result), 1)
        self.assertEqual([c['status'] for c in result[0]['cards']],
                         ['raw card', 'unreadable or unsupported'])


if __name__ == '__main__':
    unittest.main()
