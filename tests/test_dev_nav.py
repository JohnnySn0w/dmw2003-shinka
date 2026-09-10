import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from dev_nav import Navigator, load_points, validate_route


class NavTests(unittest.TestCase):
    def test_transport_errors_are_not_success(self):
        nav = Navigator(transport=lambda *_: {'ok': False, 'err': 'busy'})
        with self.assertRaisesRegex(RuntimeError, 'busy'):
            nav.where()

    def test_warp_sends_one_atomic_operation_with_observed_mode(self):
        calls = []
        def transport(cmd, _port):
            calls.append(cmd)
            if cmd['op'] == 'where':
                return dict(ok=True, schema=1, mode=0x1000 if not any(c.get('op')=='warp' for c in calls) else 0x234, queued=0)
            return dict(ok=True)
        nav = Navigator(transport=transport)
        with patch('dev_nav.time.sleep'), patch.object(nav, 'refresh', return_value=dict(stage=0x234, x=123, y=456, facing=2)):
            nav.warp(dict(stage=0x234, x=123, y=456, facing=2))
        mutations = [c for c in calls if c['op'] != 'where']
        self.assertEqual(mutations, [dict(cmd='shinka_nav', op='warp', expected_mode=0x1000,
                                         stage=0x234, x=123, y=456, facing=2)])

    def test_refresh_waits_for_the_menu_input_phase(self):
        nav = Navigator()
        closed = dict(schema=1, mode=0x21d, queued=0, quick_menu=0, quick_phase=0)
        opening = dict(closed, quick_menu=0x800b0000, quick_phase=1)
        ready = dict(opening, quick_phase=3)
        with patch.object(nav, 'where', side_effect=[closed, closed, opening, ready, closed]), \
                patch.object(nav, 'press') as press, patch('dev_nav.time.sleep'):
            self.assertEqual(nav.refresh(), closed)
        self.assertEqual([c.args for c in press.call_args_list], [('start', 8), ('triangle', 8)])

    def test_invalid_warp_sends_no_input(self):
        nav = Navigator(transport=lambda *_: self.fail('Invalid warp contacted the runtime'))
        with self.assertRaises(ValueError):
            nav.warp(dict(stage=0x600, x=1, y=2, facing=0))

    def test_route_stops_before_input_in_an_unexpected_battle(self):
        calls = []
        def transport(cmd, _port):
            calls.append(cmd)
            return dict(ok=True, schema=1, mode=0x600, queued=0)
        nav = Navigator(transport=transport)
        with self.assertRaisesRegex(RuntimeError, 'Route stopped'):
            nav.route(dict(schema=1, steps=[dict(button='up', frames=10, before=0x21d, after=0x21d)]))
        self.assertEqual(len(calls), 1)

    def test_flag_id_does_not_collide_with_flat_parser_operation(self):
        calls = []
        def transport(cmd, _port):
            calls.append(cmd)
            return dict(ok=True, schema=1, mode=0x21d, queued=0)
        Navigator(transport=transport).mutate('flag', flag=0x4011, value=0)
        self.assertEqual(calls[-1], dict(cmd='shinka_nav', op='flag', flag_id=0x4011,
                                       value=0, expected_mode=0x21d))

    def test_entire_route_validates_before_first_input(self):
        with self.assertRaises(ValueError):
            validate_route(dict(schema=1, steps=[dict(button='up', frames=301, before=0x21d, after=0x21d)]))
        with self.assertRaises(KeyError):
            validate_route(dict(schema=1, steps=[dict(button='up', frames=10, before=0x21d)]))

    def test_bookmark_does_not_apply_stored_story(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'points.json'
            path.write_text(json.dumps(dict(schema=1, points={'test': dict(stage='0x234', x=1, y=2,
                                                                         facing=0, story=6)})))
            self.assertEqual(load_points(path)['test'], dict(stage=0x234, x=1, y=2, facing=0))
            path.write_text(json.dumps(dict(schema=1, points={'central-park': dict(stage=0x234,
                                                                                x=1, y=2, facing=0)})))
            with self.assertRaisesRegex(ValueError, 'shadows'):
                load_points(path)


if __name__ == '__main__':
    unittest.main()
