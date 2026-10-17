import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools.travel_audit import TravelAudit, changed_bytes, inventory, validate_manifest


def manifest():
    return dict(schema=1, cases=[dict(name='shell-roundtrip', slot=7, source='0x21d',
                                    legs=[dict(kind='map', icon=33, stage='0x21f',
                                               move=dict(button='down', frames=8))])])


class TravelAuditTests(unittest.TestCase):
    def test_bad_late_case_is_rejected_before_input_or_output(self):
        data = manifest()
        data['cases'].append(copy.deepcopy(data['cases'][0]))
        nav = Mock()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'run'
            with self.assertRaises(ValueError):
                TravelAudit(nav).run(data, path)
            self.assertFalse(path.exists())
        self.assertEqual(nav.mock_calls, [])

    def test_unsafe_names_and_unbounded_inputs_are_rejected(self):
        for field, value in [('name', '../save'), ('slot', 10), ('source', '0x600')]:
            data = manifest()
            data['cases'][0][field] = value
            with self.assertRaises(ValueError):
                validate_manifest(data)
        for field, value in [('kind', 'warp'), ('icon', 47), ('stage', '0x600'),
                             ('move', dict(button='cross', frames=8))]:
            data = manifest()
            data['cases'][0]['legs'][0][field] = value
            with self.assertRaises(ValueError):
                validate_manifest(data)

    def test_byte_diff_reports_exact_flag_and_rejects_missing_evidence(self):
        self.assertEqual(changed_bytes({'0x8004b370': '14000000'}, {'0x8004b370': '14000000'}), [])
        self.assertEqual(changed_bytes({'0x8004b3de': '00c5'}, {'0x8004b3de': '00c7'}),
                         [dict(address='0x8004b3df', before=197, after=199)])
        with self.assertRaises(ValueError):
            changed_bytes({'0x8004b370': '14'}, {})
        with self.assertRaises(ValueError):
            changed_bytes({'0x8004b370': '14'}, {'0x8004b370': ''})

    def test_failed_leg_keeps_evidence_and_restores_without_saving(self):
        nav = Mock()
        nav.checkpoint.return_value = dict(mode=0x21d, queued=0)
        audit = TravelAudit(nav)
        with tempfile.TemporaryDirectory() as temp, patch.object(audit, 'run_leg', side_effect=RuntimeError('quest changed')):
            path = Path(temp)/'run'
            report = audit.run(manifest(), path)
            self.assertFalse(report['cases'][0]['passed'])
            self.assertEqual(json.loads((path/'report.json').read_text())['cases'][0]['error'], 'quest changed')
        self.assertEqual([c.args for c in nav.checkpoint.call_args_list], [('load', 7), ('load', 7)])

    def test_failed_restore_stops_before_next_case(self):
        nav = Mock()
        nav.checkpoint.side_effect = [dict(mode=0x21d, queued=0), RuntimeError('lost connection')]
        audit = TravelAudit(nav)
        data = manifest()
        data['cases'].append(dict(data['cases'][0], name='second'))
        with tempfile.TemporaryDirectory() as temp, patch.object(audit, 'run_leg') as leg:
            with self.assertRaisesRegex(RuntimeError, 'restore failed'):
                audit.run(data, Path(temp)/'run')
            self.assertEqual(leg.call_count, 1)

    def test_wrong_fixture_never_sends_travel_input(self):
        nav = Mock()
        nav.checkpoint.return_value = dict(mode=0x600, queued=0)
        audit = TravelAudit(nav)
        with tempfile.TemporaryDirectory() as temp, patch.object(audit, 'run_leg') as leg:
            result = audit.run(manifest(), Path(temp)/'run')
            self.assertFalse(result['cases'][0]['passed'])
            leg.assert_not_called()

    def test_same_source_with_wrong_story_is_not_the_requested_fixture(self):
        nav = Mock()
        nav.checkpoint.return_value = dict(mode=0x21d, queued=0, story=5)
        data = manifest()
        data['cases'][0]['story'] = 20
        audit = TravelAudit(nav)
        with tempfile.TemporaryDirectory() as temp, patch.object(audit, 'run_leg') as leg:
            result = audit.run(data, Path(temp)/'run')
            self.assertIn('expected story', result['cases'][0]['error'])
            leg.assert_not_called()

    def test_cursor_must_snap_to_requested_icon(self):
        nav = Mock()
        audit = TravelAudit(nav)
        with patch.object(audit, 'words', side_effect=[[0x800a0000], [0, 80, 90]]), \
                patch.object(audit, 'map_state', return_value=dict(x=92, y=102, snapped=1, icon=20)):
            with self.assertRaisesRegex(RuntimeError, 'did not select'):
                audit.select(33)
        self.assertEqual(nav.press.call_count, 100)
        self.assertFalse(any(c.args[0] == 'cross' for c in nav.press.call_args_list))

    def test_same_stage_cannot_be_misreported_as_successful_travel(self):
        nav = Mock()
        nav.where.return_value = dict(mode=0x21f)
        with self.assertRaisesRegex(ValueError, 'Same-stage'):
            TravelAudit(nav).run_leg(dict(kind='map', icon=33, stage=0x21f), Path('.'), {})
        nav.press.assert_not_called()
        nav.open_map.assert_not_called()

    def test_native_setup_flag_change_stops_before_cross(self):
        nav = Mock()
        audit = TravelAudit(nav)
        leg = dict(kind='native-exit', stage=0x22c,
                   position=dict(stage=0x22a, x=100, y=200, facing=3))
        result = {}
        with patch.object(audit, 'progression', side_effect=[{'0x8004b370': '14'}, {'0x8004b370': '15'}]), \
                patch.object(audit, 'control_snapshot', return_value=leg['position']):
            with self.assertRaisesRegex(RuntimeError, 'positioning changed'):
                audit.run_leg(leg, Path('.'), result)
        self.assertEqual(len(result['setup_changes']), 1)
        nav.press.assert_not_called()

    def test_arrival_retries_ignored_start_without_dismissing_a_scene(self):
        nav = Mock()
        closed = dict(mode=0x21f, queued=0, quick_menu=0, quick_phase=0)
        opened = dict(closed, quick_menu=0x800b0000, quick_phase=3)
        nav.where.side_effect = [closed, closed, opened]
        nav.until.return_value = closed
        self.assertEqual(TravelAudit(nav).control_snapshot(0x21f), closed)
        self.assertEqual([c.args for c in nav.press.call_args_list],
                         [('start', 2), ('neutral', 20), ('start', 2), ('neutral', 20), ('triangle', 8)])
        nav.reset_mock()
        nav.where.side_effect = [dict(closed, mode=0x600)]
        with self.assertRaisesRegex(RuntimeError, 'Scene interrupted'):
            TravelAudit(nav).control_snapshot(0x21f)
        nav.press.assert_not_called()

    def test_inventory_follows_only_trigger_referenced_records(self):
        ram = bytearray(0x200000)
        struct.pack_into('<6H3I', ram, 0x100+2*24, 0xffff, 0, 0x6005, 0, 1, 0x22c,
                         (352 << 16) | 900, 0x640003, 0)
        layer = Mock(mode=0x22a)
        layer.word.return_value = 0x80000100
        layer.regions.return_value = [dict(index=2, bank=0, sample=[200, 700])]
        with patch('tools.travel_audit.TriggerMap', return_value=layer):
            result = inventory(bytes(ram))
            self.assertEqual(len(result['triggers']), 1)
            row = result['triggers'][0]
            self.assertEqual(row['native_arrival'], dict(stage=0x22c, x=230400, y=90112, facing=3))
            self.assertEqual(row['record']['all_conditions'][1]['operator'], '!=')
            layer.word.return_value = 0x801ffff0
            with self.assertRaises(ValueError):
                inventory(bytes(ram))


if __name__ == '__main__':
    unittest.main()
