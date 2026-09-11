import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from profile_scheduler import COUNTERS, summarize, symbol_addresses


class SchedulerProfileTests(unittest.TestCase):
    def interval(self):
        before = dict(wall=10, cpu=2, enabled=1, counters={name: 100 for name in COUNTERS})
        after = dict(wall=12, cpu=3, enabled=1, counters={name: 300 for name in COUNTERS})
        after['counters']['s_frame_count'] = 200
        return before, after

    def test_rates_and_one_core_cpu(self):
        result = summarize(*self.interval())
        self.assertEqual(result['guest_hz'], 50)
        self.assertEqual(result['process_cpu_ms_per_guest_update'], 10)
        self.assertEqual(result['process_cpu_percent_one_core'], 50)
        self.assertEqual(result['per_guest_update']['shinka_cd_latched_queries'], 2)

    def test_reject_reset_or_stopped_game(self):
        before, after = self.interval()
        for name in COUNTERS:
            bad = copy.deepcopy(after)
            bad['counters'][name] = 99
            with self.assertRaises(ValueError):
                summarize(before, bad)
        after['counters']['s_frame_count'] = 100
        with self.assertRaises(ValueError):
            summarize(before, after)

    def test_reject_mode_or_clock_changes(self):
        before, after = self.interval()
        for key, value in [('enabled', 0), ('wall', 9), ('cpu', 1)]:
            bad = dict(after, **{key: value})
            with self.assertRaises(ValueError):
                summarize(before, bad)

    def test_resolve_aslr_from_preferred_base(self):
        names = (*COUNTERS, 'shinka_cd_deadline_enabled')
        text = ' Preferred load address is 0000000140000000\n'
        text += '\n'.join(f' 0003:00001000 {name} {0x140001000+i*8:016x} data.obj' for i, name in enumerate(names))
        result = symbol_addresses(text, 0x7ff600000000)
        self.assertEqual(result[COUNTERS[0]], 0x7ff600001000)
        self.assertEqual(result[names[-1]], 0x7ff600001000 + (len(names)-1)*8)

    def test_reject_missing_symbols_or_invalid_map(self):
        for text in ('', 'Preferred load address is 0000000140000000\n'):
            with self.assertRaises(ValueError):
                symbol_addresses(text, 0x1000)
