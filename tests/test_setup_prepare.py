from pathlib import Path
import io
import json
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
    def test_staging_rename_recovers_from_windows_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root/'staging', root/'ready'
            source.mkdir()
            (source/'payload').write_text('complete')
            rename = Path.rename
            locked = PermissionError('scanner lock')
            locked.winerror = 32
            attempts = []
            def transient(path, destination):
                attempts.append(path)
                if len(attempts) < 3:
                    raise locked
                return rename(path, destination)
            cancel = threading.Event()
            with patch.object(Path, 'rename', transient), patch.object(cancel, 'wait', return_value=False):
                setup.rename_staged(source, target, cancel)
            self.assertEqual(len(attempts), 3)
            self.assertEqual((target/'payload').read_text(), 'complete')
            self.assertFalse(source.exists())

    def test_staging_rename_is_cancellable_and_permanent_failures_are_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory)/'staging', Path(directory)/'ready'
            source.mkdir()
            cancel = threading.Event()
            locked = PermissionError('access denied')
            locked.winerror = 5
            with patch.object(Path, 'rename', side_effect=locked) as rename:
                with patch.object(cancel, 'wait', side_effect=lambda delay: cancel.set()):
                    with self.assertRaises(setup.Cancelled):
                        setup.rename_staged(source, target, cancel)
                self.assertEqual(rename.call_count, 1)
                cancel.clear()
                rename.reset_mock()
                with patch.object(cancel, 'wait', return_value=False):
                    with self.assertRaises(PermissionError):
                        setup.rename_staged(source, target, cancel)
                self.assertEqual(rename.call_count, 5)
            with patch.object(Path, 'rename', side_effect=FileExistsError('destination exists')) as rename:
                with self.assertRaises(FileExistsError):
                    setup.rename_staged(source, target, cancel)
                self.assertEqual(rename.call_count, 1)
            self.assertTrue(source.is_dir())
            self.assertFalse(target.exists())

    def test_corrupt_tool_marker_repairs_from_verified_cache_without_download(self):
        for marker_text in ('{broken', '[]', '{"sha256":"wrong"}'):
            with self.subTest(marker=marker_text), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                installed = root/'toolchains/test'
                installed.mkdir(parents=True)
                (installed/'shinka-verified.json').write_text(marker_text)
                (installed/'old-file').write_text('retain for diagnosis')
                (root/'cache').mkdir()
                archive = root/'cache/toolchain-test.zip'
                with zipfile.ZipFile(archive, 'w') as zipped:
                    for name in ('bin/cmake.exe', 'bin/clang.exe', 'bin/clang++.exe', 'bin/ninja.exe', 'python/python.exe'):
                        zipped.writestr(name, 'test tool')
                config = dict(version='test', sha256=setup.hash_file(archive))
                with patch.object(setup, 'TOOLCHAIN', config), patch.object(setup.urllib.request, 'urlopen') as download:
                    result = setup.ensure_toolchain(root, threading.Event(), lambda *args: None)
                download.assert_not_called()
                self.assertEqual(result, installed)
                self.assertTrue((result/'bin/clang++.exe').is_file())
                self.assertEqual(json.loads((result/'shinka-verified.json').read_text())['sha256'], config['sha256'])
                backups = list((root/'toolchains').glob('replaced-*'))
                self.assertEqual(len(backups), 1)
                self.assertEqual((backups[0]/'old-file').read_text(), 'retain for diagnosis')

    def test_cancelled_download_keeps_existing_tools_and_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed = root/'toolchains/test'
            installed.mkdir(parents=True)
            (installed/'old-file').write_bytes(b'old tools')
            (root/'launcher.json').write_bytes(b'active settings')
            cancel = threading.Event()
            class InterruptedDownload(io.BytesIO):
                def read(self, size=-1):
                    block = super().read(size)
                    cancel.set()
                    return block
            config = dict(version='test', bytes=10, sha256='unused', url='https://example.invalid/tools.zip')
            with patch.object(setup, 'TOOLCHAIN', config), patch.object(setup.urllib.request, 'urlopen', return_value=InterruptedDownload(b'test')):
                with self.assertRaises(setup.Cancelled):
                    setup.ensure_toolchain(root, cancel, lambda *args: None)
            self.assertEqual((root/'launcher.json').read_bytes(), b'active settings')
            self.assertEqual((installed/'old-file').read_bytes(), b'old tools')
            self.assertFalse(list((root/'cache').glob('*.part')))
            self.assertFalse(list((root/'toolchains').glob('.staging-*')))

    def test_codegen_path_hook_is_repeatable_and_checks_all_sites_first(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'recompiler').mkdir()
            (root/'runtime').mkdir()
            files = {
                'runtime/check_generated_sources.cmake': 'file(STRINGS "${SOURCES_FILE}" _sources)',
                'recompiler/CMakeLists.txt': 'COMMAND cmake "-DSRCS=${PSXRECOMP_CODEGEN_HASH_SRCS}"',
                'runtime/runtime.cmake': 'COMMAND cmake "-DSRCS=${_codegen_srcs}"',
                'runtime/hash_codegen.cmake': 'set(_cat "")\nforeach(f IN LISTS SRCS)\nendforeach()',
            }
            for name, text in files.items():
                (root/name).write_text(text)
            (root/'runtime/hash_codegen.cmake').write_text('unexpected revision')
            with self.assertRaisesRegex(ValueError, 'hook changed'):
                setup.configure_codegen_paths(root)
            self.assertEqual((root/'recompiler/CMakeLists.txt').read_text(), files['recompiler/CMakeLists.txt'])
            (root/'runtime/hash_codegen.cmake').write_text(files['runtime/hash_codegen.cmake'])
            setup.configure_codegen_paths(root)
            expected = {name: (root/name).read_text() for name in files}
            setup.configure_codegen_paths(root)
            self.assertEqual(expected, {name: (root/name).read_text() for name in files})
            self.assertIn('codegen_hash_sources.cmake', expected['runtime/hash_codegen.cmake'])

    def test_environment_excludes_host_compilers_and_python(self):
        with patch.dict(os.environ, {'PATH': 'host tools', 'PYTHONPATH': 'host modules', 'INCLUDE': 'host headers'}):
            env = setup.portable_environment(Path('portable tools'))
        self.assertNotIn('host', env['PATH'])
        self.assertNotIn('PYTHONPATH', env)
        self.assertNotIn('INCLUDE', env)
        self.assertEqual(env['PYTHONUTF8'], '1')
        self.assertEqual(env['PYTHONIOENCODING'], 'utf-8')

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
