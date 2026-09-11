import copy
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_battle_motion import analyze, validate_trace
from inspect_runtime_objects import MODE_ADDRESS, OWNER_ADDRESS, RAM_SIZE, SIGNATURE


class BattleMotionTests(unittest.TestCase):
    def setUp(self):
        self.ram = bytearray(RAM_SIZE)
        self.model, self.control, self.camera = 0xa0000, 0xb0000, 0x92000
        self.word(MODE_ADDRESS, 0x600)
        self.word(OWNER_ADDRESS, 0x80090000)
        self.object(0x90000, 0x800a6c44, (0x80091000, 0x80092000))
        self.object(0x91000, 0x80087bb0, (0x800a0000,))
        self.object(self.model, 0x80083e0c)
        self.object(self.camera, 0x80091df4)
        self.word(self.model + 0x64, 0x800b0000)
        self.word(self.model + 0x78, 1)
        self.word(self.camera + 0x50, 0x1001)
        self.capture = dict(models=[0x800a0000], controls=[0x800b0000],
                            spans=[(0x800a0078, 0x800a00a4), (0x800b0000, 0x800b0028),
                                   (0x80092050, 0x80092108)], trace=[])

    def word(self, address, value):
        struct.pack_into('<I', self.ram, address, value)

    def object(self, address, callback, children=()):
        self.ram[address + 0x28:address + 0x48] = SIGNATURE
        self.word(address + 0x48, callback)
        self.word(address + 0x20, len(children))
        self.word(address + 0x24, 0x80000000 + address + 0x300)
        for index, child in enumerate(children):
            self.word(address + 0x300 + index * 4, child)

    def write(self, address, old, new, pc, frame=100, width=4, ra=0x8008b8b0):
        self.capture['trace'].append(dict(seq=len(self.capture['trace']), frame=frame,
                                          addr=hex(address), old=hex(old), new=hex(new),
                                          pc=hex(pc), ra=hex(ra), w=width))

    def test_clip_handoff_and_loop_are_distinct_from_completion(self):
        self.write(self.model + 0x78, 1, 39, 0x80083a94)
        self.write(self.model + 0x80, 138, 140, 0x80083d3c, 101)
        self.write(self.model + 0x80, 140, 100, 0x80083d88, 101)
        self.write(self.control + 8, 39, 1, 0x8008b91c, 102)
        self.write(self.model + 0x78, 39, 1, 0x80083a94, 103)
        self.write(self.model + 0x7c, 0, 1, 0x80083d90, 104)
        self.write(self.control + 0x10, 0, 1, 0x80083d98, 104)
        self.capture['recorder'] = dict(total=7, available=7)
        report = analyze(self.capture, self.ram)
        actor = report['actors'][0]
        self.assertEqual(actor['clip_sequence'], [1, 39, 1])
        cast = actor['segments'][1]
        self.assertEqual((cast['loops'], cast['completions'], cast['ended_by']), (1, 0, 'clip_selection'))
        self.assertEqual(actor['advance_histogram'], {'2': 1})
        self.assertEqual([e['kind'] for e in report['events']][-2:], ['completion_set', 'completion_notified'])
        self.assertTrue(report['integrity']['recorder_totals_verified'])

    def test_same_clip_selection_starts_a_new_segment(self):
        self.write(self.model + 0x78, 1, 1, 0x80083a94)
        actor = analyze(self.capture, self.ram)['actors'][0]
        self.assertEqual(actor['clip_sequence'], [1])
        self.assertEqual(len(actor['segments']), 2)
        self.assertEqual(actor['events'][0]['kind'], 'same_clip_selected')

    def test_initial_clip_uses_first_store_old_and_tail_stays_open(self):
        self.write(self.model + 0x80, 90, 92, 0x80083d3c)
        self.write(self.model + 0x78, 7, 11, 0x80083a94, 101)
        self.word(self.model + 0x7c, 1)  # A stale snapshot latch is not an observed event.
        result = analyze(self.capture, self.ram)
        actor = result['actors'][0]
        self.assertEqual(actor['initial_clip'], 7)
        self.assertEqual(actor['initial_clip_source'], 'first_store_old')
        self.assertTrue(actor['segments'][0]['began_before_capture'])
        self.assertEqual(actor['segments'][-1]['ended_by'], 'capture_end')
        self.assertEqual(sum(s['completions'] for s in actor['segments']), 0)
        self.assertFalse(result['integrity']['recorder_totals_verified'])

    def test_aliases_are_normalized_for_fields_and_ownership(self):
        self.capture['models'] = [0xa00a0000]
        self.capture['controls'] = [0xb0000]
        self.write(0xa00a0080, 1, 5, 0xa0083d3c)
        actor = analyze(self.capture, self.ram)['actors'][0]
        self.assertEqual(actor['advance_histogram'], {'4': 1})

    def test_environment_model_with_same_callback_is_rejected(self):
        self.object(0xc0000, 0x80083e0c)
        self.object(0x90000, 0x800a6c44, (0x80091000, 0x800c0000))
        self.capture['models'] = [0x800c0000]
        self.write(self.model + 0x80, 1, 3, 0x80083d3c)
        with self.assertRaisesRegex(ValueError, 'ownership'):
            analyze(self.capture, self.ram)

    def test_missing_control_coverage_rejects_event_inference(self):
        self.capture['spans'].pop(1)
        self.write(self.model + 0x80, 1, 3, 0x80083d3c)
        with self.assertRaisesRegex(ValueError, 'coverage'):
            analyze(self.capture, self.ram)

    def test_partial_semantic_field_needs_new_decoder(self):
        self.write(self.model + 0x7a, 0, 1, 0x80083a94, width=2)
        with self.assertRaisesRegex(ValueError, 'Partial'):
            analyze(self.capture, self.ram)

    def test_overlapping_byte_history_checks_halfword_writes(self):
        self.write(self.camera + 0x54, 0, 0x12345678, 0x80092264)
        self.write(self.camera + 0x56, 0x1234, 0xabcd, 0x8009205c, width=2)
        self.write(self.camera + 0x54, 0xabcd5678, 0, 0x80092264)
        validate_trace(self.capture)
        self.capture['trace'][-1]['old'] = '0x12345678'
        with self.assertRaisesRegex(ValueError, 'continuity'):
            validate_trace(self.capture)

    def test_recorder_overflow_and_missing_tail_are_rejected(self):
        self.write(self.model + 0x80, 1, 3, 0x80083d3c)
        for total, available in ((2, 1), (2, 2)):
            self.capture['recorder'] = dict(total=total, available=available)
            with self.assertRaisesRegex(ValueError, 'totals'):
                validate_trace(self.capture)

    def test_sequence_gaps_duplicates_and_frame_reversal_are_rejected(self):
        self.write(self.model + 0x80, 1, 3, 0x80083d3c)
        self.write(self.model + 0x80, 3, 5, 0x80083d3c, 101)
        for index, key, value in ((0, 'seq', 1), (1, 'seq', 0), (1, 'seq', 2), (1, 'frame', 99)):
            bad = copy.deepcopy(self.capture)
            bad['trace'][index][key] = value
            with self.assertRaisesRegex(ValueError, 'ordered'):
                validate_trace(bad)

    def test_direct_camera_sets_do_not_claim_interpolation(self):
        self.write(self.camera + 0xf0, 4096, 4096, 0x80092290, ra=0x80087adc)
        self.write(self.camera + 0xf0, 4096, 4096, 0x80092290, 101, ra=0x8008c204)
        camera = analyze(self.capture, self.ram)['cameras'][0]
        self.assertEqual((camera['direct_sets'], camera['interpolation_updates']), (2, 0))
        self.assertEqual(camera['setter_callers'], {'0x80087ADC': 1, '0x8008C204': 1})

    def test_camera_and_model_events_preserve_same_frame_order(self):
        self.write(self.model + 0x7c, 0, 1, 0x80083d90)
        self.write(self.camera + 0xf0, 100, 200, 0x80091ee0)
        self.write(self.control + 8, 15, 16, 0x8008b8f0)
        report = analyze(self.capture, self.ram)
        self.assertEqual([e['kind'] for e in report['events']],
                         ['completion_set', 'camera_advance', 'clip_requested'])
        self.assertEqual([e['seq'] for e in report['events']], [0, 1, 2])
        self.assertEqual(report['cameras'][0]['interpolation_updates'], 1)

    def test_invalid_mmio_and_outside_watch_writes_are_rejected(self):
        self.write(self.model + 0x80, 1, 3, 0x80083d3c)
        for address in ('0xbf801810', '0x801fffff', '0x80010000'):
            bad = copy.deepcopy(self.capture)
            bad['trace'][0]['addr'] = address
            with self.assertRaises(ValueError):
                validate_trace(bad)


if __name__ == '__main__':
    unittest.main()
