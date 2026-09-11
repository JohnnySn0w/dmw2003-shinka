import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from generate_menu_hooks import card_transfer_hooks, shard


class CardTransferHookTests(unittest.TestCase):
    SOURCE = '''    { uint32_t _pgx1 = cpu->gpr[2]; cpu->gpr[2] = cpu->gpr[2] + 128;
    PGXP_ALU(0x24420080u, cpu->gpr[2], _pgx1, 0x00000080u); }  /* 0x80014EE8: 0x24420080 */
    { uint32_t _pgx1 = cpu->gpr[0]; cpu->gpr[17] = 128;
    PGXP_ALU(0x24110080u, cpu->gpr[17], _pgx1, 0x00000080u); }  /* 0x80014F04: 0x24110080 */'''

    def test_requires_both_exact_read_sites(self):
        for code in ('', self.SOURCE * 2, self.SOURCE.replace('80014EE8', '800151A8'),
                     self.SOURCE.replace('+ 128;', '+ 256;')):
            with self.assertRaises(ValueError):
                card_transfer_hooks(code)

    def test_preserves_surrounding_io_and_matches_progress(self):
        code = '/* initial request */\n' + self.SOURCE + '\n/* retry and error handling */'
        result = card_transfer_hooks(code)
        self.assertTrue(result.startswith('/* initial request */'))
        self.assertTrue(result.endswith('/* retry and error handling */'))
        self.assertIn('shinka_card_transfer_completed(cpu->gpr[19], cpu->gpr[2], cpu->read_word(0x800828ecu))', result)
        self.assertIn('shinka_card_read_chunk(cpu->gpr[19], cpu->read_word(0x80048a50u))', result)
        self.assertEqual(result.count('_pgx1, _card_chunk)'), 2)

    def test_read_hook_leaves_write_wrapper_unchanged(self):
        writes = self.SOURCE.replace('80014EE8', '800151AC').replace('80014F04', '800151C8')
        result = card_transfer_hooks(self.SOURCE + '\n' + writes)
        self.assertTrue(result.endswith(writes))

    def test_write_batching_targets_only_write_wrapper(self):
        writes = self.SOURCE.replace('80014EE8', '800151AC').replace('80014F04', '800151C8')
        result = card_transfer_hooks(self.SOURCE + '\n' + writes, write=True)
        self.assertTrue(result.startswith(self.SOURCE))
        self.assertIn('shinka_card_write_chunk(cpu->gpr[19], cpu->read_word(0x80048a50u))', result)
        self.assertIn('shinka_card_transfer_completed', result)
        for code in (self.SOURCE, writes * 2, writes.replace('800151AC', '800151A8')):
            with self.assertRaises(ValueError):
                card_transfer_hooks(code, write=True)


class FrameHookTests(unittest.TestCase):
    SITE = '    PGXP_ALU(0x24020001u, cpu->gpr[2], _pgx1, 0x00000001u); }  /* 0x8001D5A0: 0x24020001 */'
    ENTRY = '    debug_server_log_call_entry(0x8001D504u);'

    def test_requires_the_verified_draw_sync_return(self):
        for code in ('', self.SITE + '\n' + self.SITE,
                     self.SITE.replace('8001D5A0', '8001D598')):
            with self.assertRaises(ValueError):
                shard(self.ENTRY + '\n' + code, '04')

    def test_hook_follows_the_resume_site(self):
        code = '#include "SLES_039.36_decls.h"\n' + self.ENTRY + '\n' + self.SITE + '\n/* buffer exchange */'
        result = shard(code, '04')
        self.assertLess(result.index(self.SITE), result.index('    shinka_map_present();'))
        self.assertLess(result.index('    shinka_map_present();'), result.index('/* buffer exchange */'))
        self.assertLess(result.index('if (cpu->gpr[4]) shinka_field_prepare();'), result.index(self.SITE))

    def test_field_hook_rejects_changed_or_duplicate_entry(self):
        for entry in ('', self.ENTRY * 2, self.ENTRY.replace('8001D504', '8001D508')):
            with self.assertRaises(ValueError):
                shard(entry + '\n' + self.SITE, '04')


if __name__ == '__main__':
    unittest.main()
