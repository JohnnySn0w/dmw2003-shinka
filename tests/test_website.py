from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from check_website import check


class WebsiteTests(unittest.TestCase):
    def check_page(self, html, files=()):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'index.html').write_text(html, encoding='utf-8')
            for name, content in files:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(content, encoding='utf-8')
            return check(root)

    def test_relative_assets_and_cross_page_anchors(self):
        errors = self.check_page(
            '<img alt="Chart" src="media/chart%20hint.png">'
            '<a href="notes.html#method">Method</a>',
            [('media/chart hint.png', ''), ('notes.html', '<h1 id="method">Method</h1>')])
        self.assertEqual(errors, [])

    def test_missing_gif_and_broken_anchor(self):
        errors = self.check_page('<img id="demo" alt="Chart" data-gif="missing.gif">'
                                 '<a href="#missing">Next</a>')
        self.assertTrue(any('missing asset' in error for error in errors))
        self.assertTrue(any('missing anchor' in error for error in errors))

    def test_bad_gif_target_and_duplicate_id(self):
        errors = self.check_page('<div id="x"></div><div id="x"></div>'
                                 '<button data-toggle="missing">Play</button>')
        self.assertTrue(any('Duplicate id' in error for error in errors))
        self.assertTrue(any('missing GIF target' in error for error in errors))

    def test_media_must_be_user_controlled(self):
        errors = self.check_page('<video autoplay></video><img src="poster.png">',
                                 [('poster.png', '')])
        self.assertTrue(any('playback controls' in error for error in errors))
        self.assertTrue(any('autoplay' in error for error in errors))
        self.assertTrue(any('alt text' in error for error in errors))

    def test_project_hosting_rejects_root_and_parent_paths(self):
        errors = self.check_page('<a href="/style.css">Root</a><a href="../card.mcd">Parent</a>')
        self.assertTrue(any('root-relative' in error for error in errors))
        self.assertTrue(any('leaves published directory' in error for error in errors))


if __name__ == '__main__':
    unittest.main()
