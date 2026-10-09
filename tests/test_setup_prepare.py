from pathlib import Path
import os
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import setup_prepare as setup


class PreparationTests(unittest.TestCase):
    def test_environment_excludes_host_compilers_and_python(self):
        with patch.dict(os.environ, {'PATH': 'host tools', 'PYTHONPATH': 'host modules', 'INCLUDE': 'host headers'}):
            env = setup.portable_environment(Path('portable tools'))
        self.assertNotIn('host', env['PATH'])
        self.assertNotIn('PYTHONPATH', env)
        self.assertNotIn('INCLUDE', env)

    def test_interrupted_source_is_not_reused_and_completed_source_is(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sdk = root/'sdk.zip'
            with zipfile.ZipFile(sdk, 'w') as archive:
                archive.writestr('sdk-manifest.json', '{}')
                archive.writestr('file.txt', 'complete')
            (root/'source').mkdir()
            (root/'source/file.txt').write_text('interrupted')
            cancel = threading.Event()
            cancel.set()
            with self.assertRaises(setup.Cancelled):
                setup.extract_source(sdk, root, cancel)
            self.assertEqual((root/'source/file.txt').read_text(), 'interrupted')
            cancel.clear()
            setup.extract_source(sdk, root, cancel)
            self.assertEqual((root/'source/file.txt').read_text(), 'complete')
            self.assertTrue(list(root.glob('source-interrupted-*')))
            with patch.object(setup, 'safe_extract', side_effect=AssertionError('should reuse')):
                setup.extract_source(sdk, root, cancel)

    def test_low_disk_space_stops_before_disc_reads_or_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(setup.shutil, 'disk_usage') as usage, patch.object(setup, 'validate_disc') as disc:
                usage.return_value.free = 1
                with self.assertRaisesRegex(OSError, '6 GB'):
                    setup.prepare('unused.cue', 'unused.zip', directory)
                disc.assert_not_called()


if __name__ == '__main__':
    unittest.main()
