import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from generate_menu_hooks import shard


class FrameHookTests(unittest.TestCase):
    SITE = '    PGXP_ALU(0x24020001u, cpu->gpr[2], _pgx1, 0x00000001u); }  /* 0x8001D5A0: 0x24020001 */'

    def test_requires_the_verified_draw_sync_return(self):
        for code in ('', self.SITE + '\n' + self.SITE,
                     self.SITE.replace('8001D5A0', '8001D598')):
            with self.assertRaises(ValueError):
                shard(code, '04')

    def test_hook_follows_the_resume_site(self):
        code = '#include "SLES_039.36_decls.h"\n' + self.SITE + '\n/* buffer exchange */'
        result = shard(code, '04')
        self.assertLess(result.index(self.SITE), result.index('    shinka_map_present();'))
        self.assertLess(result.index('    shinka_map_present();'), result.index('/* buffer exchange */'))


if __name__ == '__main__':
    unittest.main()
