import sys
import tomllib
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from configure_journal import select_journal


class JournalConfigTests(unittest.TestCase):
    def test_preserves_exp_and_other_features(self):
        original = '''format_version = 2
[[package]]
id = "shinka.experience"
version = "0.1.0"
[[feature]]
package_id = "shinka.experience"
id = "dv-exp"
enabled = true
[feature.values]
fixed_award = "10"
multiplier = "1"
'''
        enabled = select_journal(original, True)
        disabled = tomllib.loads(select_journal(enabled, False))
        self.assertEqual(disabled['feature'][0], tomllib.loads(original)['feature'][0])
        self.assertFalse(disabled['feature'][1]['enabled'])
        self.assertEqual(len(disabled['package']), 2)

    def test_rejects_unknown_schema(self):
        with self.assertRaises(ValueError):
            select_journal('format_version = 9', True)
