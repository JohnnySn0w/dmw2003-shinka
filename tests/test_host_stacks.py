import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from summarize_host_stacks import map_symbols, summarize

MAP = '''Preferred load address is 0000000140000000
 0001:00000000 callee 0000000140001000 f worker.obj
 0001:00000100 caller 0000000140001100 f worker.obj
 0001:00000200 folded_a 0000000140001200 f a.obj
 0001:00000200 folded_b 0000000140001200 f b.obj
 0002:00000000 data 0000000140010000   data.obj
'''


class HostStackTests(unittest.TestCase):
    def setUp(self):
        self.game = dict(base=0x200000, size=0x20000, path='C:\\test\\dmw2003-shinka.exe')
        self.symbols = map_symbols(MAP, self.game['base'])

    def report(self, stacks):
        return summarize(dict(modules=[self.game, dict(base=0x900000, size=0x1000, path='C:\\Windows\\wait.dll')],
                              samples=[dict(pcs=pcs, stop_us=10, truncated=False) for pcs in stacks],
                              wall_seconds=1, thread_cpu_seconds=.5), self.symbols, self.game)

    def test_aslr_functions_and_folded_aliases(self):
        self.assertEqual(self.symbols, [(0x201000, 'callee', 'worker.obj'),
                                       (0x201100, 'caller', 'worker.obj'),
                                       (0x201200, 'folded_a|folded_b', 'a.obj|b.obj')])

    def test_recursive_frames_count_once_inclusive(self):
        result = self.report([[0x201010, 0x201030, 0x201120]])
        counts = {row['name']: row['samples'] for row in result['inclusive']}
        self.assertEqual(counts, dict(callee=1, caller=1))
        self.assertEqual(result['leaf'][0]['name'], 'callee')

    def test_return_address_boundary_belongs_to_caller_instruction(self):
        result = self.report([[0x201010, 0x201200]])
        self.assertIn('caller;callee', result['folded'])

    def test_waits_and_unknown_addresses_are_not_assigned_game_cost(self):
        result = self.report([[0x900010, 0x201120], [0x800000]])
        self.assertEqual({r['name'] for r in result['leaf']}, {'wait.dll+0x10', 'unknown+0x800000'})
        self.assertEqual(result['single_frame_samples'], 1)
        self.assertEqual(sum(r['sample_percent'] for r in result['leaf']), 100)

    def test_reject_empty_samples_or_invalid_map(self):
        with self.assertRaises(ValueError):
            self.report([])
        with self.assertRaises(ValueError):
            self.report([[]])
        with self.assertRaises(ValueError):
            map_symbols('wrong file', 0x200000)


if __name__ == '__main__':
    unittest.main()
