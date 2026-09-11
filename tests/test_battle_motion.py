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

    def script(self, callback=0x8008c590):
        address = 0xc0000
        self.object(address, callback)
        self.capture['scripts'] = [0x800c0000]
        self.capture['spans'].append((address, address + 0xb4))
        return address

    def registers(self, **values):
        self.capture['trace'][-1].update({key: hex(value) for key, value in values.items()})

    def test_reused_menu_storage_is_decoded_only_during_script_lifetime(self):
        script = self.script(0x80093e44)
        self.write(script + 0x8c, 0, 2, 0x8008c480)  # Same store PC, wrong owner: ignored.
        self.write(script + 0x48, 0x80093e44, 0x8008c590, 0x800144bc)
        self.write(script + 0x8c, 2, 4, 0x8008c480)
        self.registers(a0=99, a1=0)
        self.write(script + 0x48, 0x8008c590, 0, 0x80017cec)
        self.write(script + 0x8c, 4, 6, 0x8008c480)
        self.write(script + 0x48, 0, 0x8008c590, 0x800144bc, 101)
        report = analyze(self.capture, self.ram)
        self.assertEqual([e['kind'] for e in report['events']],
                         ['script_activated', 'sound_command', 'script_deactivated', 'script_activated'])
        summary = report['scripts'][0]
        self.assertEqual(summary['ignored_non_script_writes'], 2)
        self.assertEqual([l['ended_by'] for l in summary['lifetimes']], ['callback_replaced', 'capture_end'])
        self.assertEqual([l['epoch'] for l in summary['lifetimes']], [1, 2])
        self.assertEqual(report['events'][1]['selector'], 99)  # Preserve unresolved selector.

    def test_script_cursor_halfwords_and_retry_attempts(self):
        script = self.script()
        cursor = 0xa0190086
        self.write(script + 0x8c, cursor, cursor + 2, 0x8008c724)
        self.registers(s1=script, v1=2)
        self.write(script + 0x8c, cursor + 2, cursor + 8, 0x8008b880)
        self.write(script + 0x8c, cursor + 8, cursor, 0x8008bb14)
        self.registers(s1=0)
        self.write(script + 0x8c, cursor, cursor + 2, 0x8008c724, 102)
        self.registers(s1=0xa00c0000, v1=2)
        report = analyze(self.capture, self.ram)
        command = report['scripts'][0]['commands'][0]
        self.assertEqual((command['cursor'], command['attempts']), ('0x80190086', 2))
        self.assertEqual((command['first_frame'], command['last_frame']), (100, 102))
        self.assertEqual(report['scripts'][0]['waits'], {'clip_completion_wait': 1})

    def test_script_delay_underflow_means_elapsed_not_a_huge_delay(self):
        script = self.script()
        self.write(script + 0x9c, 0, 2, 0x8008c268)
        self.write(script + 0x9c, 2, 0xffffffff, 0x8008c28c, 101)
        self.write(script + 0x9c, 0xffffffff, 0, 0x8008c2ac, 101)
        report = analyze(self.capture, self.ram)
        self.assertEqual([e['kind'] for e in report['events']], ['script_delay_started', 'script_delay_elapsed'])
        self.assertEqual(report['events'][0]['duration'], 2)
        self.assertEqual(report['scripts'][0]['waits'], {'script_delay_updates': 1})

    def test_effect_wait_at_shared_rewind_site_is_not_a_clip_wait(self):
        script = self.script()
        self.write(script + 0x8c, 0x80190008, 0x80190000, 0x8008bb14)
        self.registers(s1=5)
        self.write(script + 0x8c, 0x80190000, 0x8018fffa, 0x8008be74)
        report = analyze(self.capture, self.ram)
        self.assertEqual(report['scripts'][0]['waits'], {'actor_command_5_wait': 1, 'effect_resource_wait': 1})

    def test_effect_command_records_request_selector_without_resolving_it(self):
        script = self.script()
        self.write(script + 0x8c, 0x80190004, 0x80190006, 0x8008c31c)
        self.registers(s0=0x38, a2=0)
        event = analyze(self.capture, self.ram)['events'][0]
        self.assertEqual((event['kind'], event['selector'], event['operation']), ('effect_command', 0x38, 0))

    def test_script_register_evidence_is_required_and_owner_must_match(self):
        script = self.script()
        self.write(script + 0x8c, 0x80190000, 0x80190002, 0x8008c724)
        with self.assertRaisesRegex(ValueError, 'Missing s1'):
            analyze(self.capture, self.ram)
        self.registers(s1=0x800d0000, v1=2)
        with self.assertRaisesRegex(ValueError, 'does not match'):
            analyze(self.capture, self.ram)

    def test_script_lead_needs_full_coverage_and_word_writes(self):
        script = self.script()
        self.write(script + 0x48, 0x8008c590, 0, 0x80017cec)
        self.capture['spans'][-1] = (script, script + 0xb0)
        with self.assertRaisesRegex(ValueError, 'coverage'):
            analyze(self.capture, self.ram)
        self.capture['spans'][-1] = (script, script + 0xb4)
        self.capture['trace'] = []
        self.write(script + 0x4a, 0x8008, 0, 0x80017cec, width=2)
        with self.assertRaisesRegex(ValueError, 'Partial script'):
            analyze(self.capture, self.ram)

    def test_script_initial_owner_comes_from_first_old_callback_when_available(self):
        script = self.script(0x80093e44)
        self.write(script + 0x9c, 0, 15, 0x8008c268)
        self.write(script + 0x48, 0x8008c590, 0, 0x80017cec)
        report = analyze(self.capture, self.ram)
        self.assertTrue(report['scripts'][0]['lifetimes'][0]['began_before_capture'])
        self.assertEqual(report['events'][0]['kind'], 'script_delay_started')

    def test_battle_hp_subtraction_and_clamp_are_one_ordered_pair(self):
        self.capture['spans'].append((0xa44d0, 0xa44f0))
        struct.pack_into('<7H', self.ram, 0xa44d0, 32, 0, 0, 120, 120, 9999, 9999)
        self.write(0xa44d8, 120, 0xfd49, 0x8008d064, width=2)
        self.write(0xa44d8, 0xfd49, 0, 0x8008d074, width=2)
        report = analyze(self.capture, self.ram)
        self.assertEqual(report['battle_stats'][0]['slot'], 3)
        self.assertEqual(report['battle_stats'][0]['max_hp'], 120)
        self.assertEqual([e['kind'] for e in report['events']], ['basic_hp_subtract', 'basic_hp_clamp'])
        self.assertEqual(report['events'][0]['new_signed'], -695)
        self.assertEqual(report['events'][1]['new'], 0)

    def test_technique_hp_and_early_mp_updates_are_separate(self):
        self.capture['spans'].append((0xa4470, 0xa4530))
        self.write(0xa447c, 1231, 1207, 0x80096de0, width=2)
        self.write(0xa44d8, 120, 0xfec0, 0x8008fbc0, 110, width=2)
        self.write(0xa44d8, 0xfec0, 0, 0x8008fbd4, 110, width=2)
        report = analyze(self.capture, self.ram)
        self.assertEqual([e['kind'] for e in report['events']],
                         ['battle_mp_write', 'technique_hp_subtract', 'technique_hp_clamp'])
        self.assertEqual(report['events'][1]['new_signed'], -320)
        self.assertEqual(report['events'][0]['old'] - report['events'][0]['new'], 24)

    def test_unrecognized_hp_writer_stays_visible_and_mixed_width_is_rejected(self):
        self.capture['spans'].append((0xa4470, 0xa4490))
        self.write(0xa4478, 120, 115, 0x80090000, width=2)
        self.assertEqual(analyze(self.capture, self.ram)['events'][0]['kind'], 'battle_hp_write')
        self.capture['trace'] = []
        self.write(0xa4476, 0, 1, 0x80090000, width=2)  # Max HP is not current HP.
        self.assertEqual(analyze(self.capture, self.ram)['events'], [])
        self.capture['trace'] = []
        self.write(0xa4478, 120, 115, 0x80090000, width=4)
        with self.assertRaisesRegex(ValueError, 'Non-halfword'):
            analyze(self.capture, self.ram)

    def test_prepared_damage_is_separate_from_later_hp_commit(self):
        self.capture['spans'].append((0xa43f4, 0xa4530))
        self.write(0xa441c, 0, 815, 0x8009e234)
        self.write(self.model + 0x78, 1, 15, 0x80083a94, 180)
        self.write(0xa44d8, 120, 0xfd49, 0x8008d064, 436, width=2)
        self.write(0xa44d8, 0xfd49, 0, 0x8008d074, 436, width=2)
        events = analyze(self.capture, self.ram)['events']
        self.assertEqual([e['kind'] for e in events],
                         ['basic_damage_prepared', 'clip_selected', 'basic_hp_subtract', 'basic_hp_clamp'])
        self.assertEqual(events[0]['new'], 815)
        self.assertEqual(events[2]['old'] - events[2]['new_signed'], 815)


if __name__ == '__main__':
    unittest.main()
