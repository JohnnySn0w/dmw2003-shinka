import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import setup_core as setup


class SetupTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.binary = self.root/'game dump.bin'
        self.binary.write_bytes(b'a test disc, not game data')
        self.cue = self.root/'game.cue'
        self.cue.write_text('FILE "game dump.bin" BINARY\n TRACK 01 MODE2/2352\n INDEX 01 00:00:00\n')

    def disc(self):
        with patch.object(setup, 'DISC_SHA1', hashlib.sha1(self.binary.read_bytes()).hexdigest()):
            return setup.validate_disc(self.cue)

    def test_disc_validated_then_movement_detected(self):
        disc = self.disc()
        with patch.object(setup, 'DISC_SHA1', disc['sha1']):
            self.assertTrue(setup.remembered_disc_ok(disc))
            self.binary.rename(self.root/'moved.bin')
            self.assertFalse(setup.remembered_disc_ok(disc))

    def test_reject_wrong_disc_without_writes(self):
        before = self.binary.read_bytes()
        with self.assertRaisesRegex(ValueError, 'does not match'):
            setup.validate_disc(self.cue)
        self.assertEqual(before, self.binary.read_bytes())

    def test_unsupported_cue_layouts_and_external_references(self):
        for text in ('FILE "//server/a.bin" BINARY\nTRACK 01 MODE2/2352\nINDEX 01 00:00:00',
                     'FILE "C:\\a.bin" BINARY\nTRACK 01 MODE2/2352\nINDEX 01 00:00:00',
                     'FILE "game dump.bin" BINARY\nTRACK 01 MODE1/2048\nINDEX 01 00:00:00',
                     'FILE "a.bin" BINARY\nFILE "b.bin" BINARY'):
            with self.subTest(text=text):
                self.cue.write_text(text)
                with self.assertRaises(ValueError):
                    setup.cue_bin(self.cue)

    def test_cancellation_and_modified_file_hash(self):
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(setup.Cancelled):
            setup.hash_file(self.binary, cancel=cancel)
        def modify(*args):
            self.binary.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            setup.hash_file(self.binary, progress=modify)

    def test_archive_preflight_rejects_traversal_aliases_duplicates(self):
        for names in (['../escape'], ['ok', 'dir/../../escape'], ['CON'], ['a.'], ['a', 'A'], ['C:/escape'], ['a\\b']):
            archive = self.root/'test.zip'
            with zipfile.ZipFile(archive, 'w') as zipped:
                for name in names:
                    info = zipfile.ZipInfo('placeholder')
                    info.filename = name  # avoid ZipInfo's Windows slash normalization
                    zipped.writestr(info, 'payload')
            with self.subTest(names=names), self.assertRaises(ValueError):
                setup.safe_extract(archive, self.root/'staging')
            self.assertFalse((self.root/'staging').exists())

    def test_archive_extract_cancel_and_limit(self):
        archive = self.root/'test.zip'
        with zipfile.ZipFile(archive, 'w') as zipped:
            zipped.writestr('dir/file.txt', 'payload')
        with self.assertRaises(ValueError):
            setup.safe_extract(archive, self.root/'small', max_bytes=2)
        setup.safe_extract(archive, self.root/'good')
        self.assertEqual((self.root/'good/dir/file.txt').read_text(), 'payload')
        with self.assertRaises(FileExistsError):
            setup.safe_extract(archive, self.root/'good')

    def test_discovery_configured_directory_and_invalid_cards(self):
        (self.root/'elsewhere').mkdir()
        card = self.root/'elsewhere/card.mcd'
        card.write_bytes(b'MC' + bytes(128*1024-2))
        (self.root/'settings.ini').write_text('[Folders]\nMemoryCards = elsewhere\n')
        (self.root/'bad.mcr').write_bytes(b'bad')
        cards, errors = setup.discover_cards([self.root, self.root/'elsewhere'])
        self.assertEqual([c['path'] for c in cards], [str(card.resolve())])
        self.assertEqual(len(errors), 1)

    def prepared(self, name):
        runtime = self.root/name
        runtime.mkdir()
        (runtime/'dmw2003-shinka.exe').write_bytes(b'fake executable')
        return dict(runtime=str(runtime), revision=name, disc=self.disc(), sdk={'sdk_sha256': name})

    def test_update_preserves_profile_preferences_and_settings(self):
        first = self.prepared('first')
        state = setup.activate(self.root, first)
        (Path(first['runtime'])/'settings.toml').write_text('my settings')
        card = Path(state['profile'])/'card1.mcd'
        card.write_bytes(b'original saved bytes')
        second = self.prepared('second')
        updated = setup.activate(self.root, second)
        self.assertEqual(updated['profile'], state['profile'])
        self.assertEqual(card.read_bytes(), b'original saved bytes')
        self.assertEqual((Path(second['runtime'])/'settings.toml').read_text(), 'my settings')
        self.assertEqual(updated['sdk'], second['sdk'])

    def test_relocated_disc_repair_preserves_runtime_profile_and_card(self):
        prepared = self.prepared('runtime')
        state = setup.activate(self.root, prepared)
        card = Path(state['profile'])/'card1.mcd'
        card.write_bytes(b'player progress')
        moved = self.root/'Moved disc'
        moved.mkdir()
        self.binary.rename(moved/self.binary.name)
        self.cue.rename(moved/self.cue.name)
        with patch.object(setup, 'DISC_SHA1', state['disc']['sha1']):
            with self.assertRaisesRegex(FileNotFoundError, 'moved or changed'):
                setup.launch_command(state)
            self.assertEqual(setup.read_settings(self.root), state)
            prepared['disc'] = setup.validate_disc(moved/self.cue.name)
            repaired = setup.activate(self.root, prepared)
            command = setup.launch_command(repaired)
        self.assertEqual(repaired['runtime'], state['runtime'])
        self.assertEqual(repaired['profile'], state['profile'])
        self.assertEqual(card.read_bytes(), b'player progress')
        self.assertIn(str(moved/self.cue.name), command)

    def test_bad_import_and_failed_commit_keep_active_install(self):
        state = setup.activate(self.root, self.prepared('first'))
        second = self.prepared('second')
        bad = self.root/'bad.mcd'
        bad.write_bytes(b'bad')
        with self.assertRaises(ValueError):
            setup.activate(self.root, second, bad)
        self.assertEqual(setup.read_settings(self.root), state)
        with patch.object(setup.os, 'replace', side_effect=OSError('disk error')):
            with self.assertRaises(OSError):
                setup.activate(self.root, second)
        self.assertEqual(setup.read_settings(self.root), state)

    def test_import_new_profile_preserves_original(self):
        card = self.root/'source.mcd'
        payload = b'MC' + bytes(128*1024-2)
        card.write_bytes(payload)
        state = setup.activate(self.root, self.prepared('runtime'), card, 2)
        self.assertEqual((Path(state['profile'])/'card2.mcd').read_bytes(), payload)
        self.assertEqual(card.read_bytes(), payload)

    def test_launch_explicit_arguments_and_missing_save_rejected(self):
        state = setup.activate(self.root, self.prepared('runtime'))
        with patch.object(setup, 'DISC_SHA1', state['disc']['sha1']):
            command = setup.launch_command(state)
            self.assertIn(str(self.cue), command)
            self.assertIn(state['profile'], command)
            Path(state['profile']).rmdir()
            with self.assertRaisesRegex(FileNotFoundError, 'blank replacement'):
                setup.launch_command(state)


if __name__ == '__main__':
    unittest.main()
