import copy
import sys
import struct
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from profile_scheduler import COUNTERS, summarize, symbol_addresses, validate_loaded_image


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


class LoadedImageTests(unittest.TestCase):
    def setUp(self):
        self.base = 0x7ff600000000
        self.image = bytearray(512)
        self.image[:2] = b'MZ'
        struct.pack_into('<I', self.image, 60, 128)
        self.image[128:132] = b'PE\0\0'
        struct.pack_into('<H', self.image, 132, 0x8664)
        struct.pack_into('<I', self.image, 136, 0x12345678)
        struct.pack_into('<H', self.image, 152, 0x20b)
        struct.pack_into('<Q', self.image, 176, 0x140000000)
        struct.pack_into('<I', self.image, 208, 0x90000)
        self.text = 'Timestamp is 12345678\nPreferred load address is 0000000140000000\n'

    def validate(self, text=None, base=None):
        def read(address, size):
            offset = address - self.base
            return bytes(self.image[offset:offset+size])
        return validate_loaded_image(self.text if text is None else text,
                                     self.base if base is None else base, read)

    def test_aslr_identity_uses_loaded_headers(self):
        self.assertEqual(self.validate(), dict(timestamp=0x12345678, preferred_base=0x140000000,
                                              header_base=0x140000000, loaded_base=self.base, size=0x90000))

    def test_loader_may_rewrite_image_base_to_aslr_address(self):
        struct.pack_into('<Q', self.image, 176, self.base)
        self.assertEqual(self.validate()['header_base'], self.base)
        self.assertEqual(self.validate()['preferred_base'], 0x140000000)
        with self.assertRaises(ValueError):
            validate_loaded_image(self.text, 0, lambda offset, size: bytes(self.image[offset:offset+size]),
                                  allow_relocated_header=False)

    def test_reject_stale_map_timestamp_and_preferred_base(self):
        for text in (self.text.replace('12345678', '12345679'),
                     self.text.replace('140000000', '150000000'), ''):
            with self.assertRaises(ValueError):
                self.validate(text)

    def test_reject_wrong_module_base_or_truncated_headers(self):
        with self.assertRaises(ValueError):
            self.validate(base=self.base+1)
        self.image = self.image[:150]
        with self.assertRaises(ValueError):
            self.validate()

    def test_reject_non_x64_images(self):
        struct.pack_into('<H', self.image, 132, 0x14c)
        with self.assertRaises(ValueError):
            self.validate()
        struct.pack_into('<H', self.image, 132, 0x8664)
        struct.pack_into('<H', self.image, 152, 0x10b)
        with self.assertRaises(ValueError):
            self.validate()

    def test_reject_invalid_header_offset_or_image_size(self):
        struct.pack_into('<I', self.image, 60, 0xffffffff)
        with self.assertRaises(ValueError):
            self.validate()
        struct.pack_into('<I', self.image, 60, 128)
        struct.pack_into('<I', self.image, 208, 32)
        with self.assertRaises(ValueError):
            self.validate()
