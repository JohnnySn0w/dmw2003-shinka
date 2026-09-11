"""Generate a guarded Shinka copy of the pinned SPU, preserving guest state."""
import argparse
from pathlib import Path


def hooks(code):
    def replace(old, new):
        nonlocal code
        if code.count(old) != 1:
            raise ValueError(f'Review pinned SPU music hook: {old[:70]}')
        code = code.replace(old, new)
    replace('#include "spu.h"', '#include "spu.h"\n#include "music_live.h"\nextern int shinka_music_palette_get(void);\nstatic int shinka_palette;\nstatic int16_t shinka_original[24];')
    replace('    if (!v->active) return 0;', '    shinka_original[idx] = 0;\n    if (!v->active) return 0;')
    replace('    /* Apply envelope (0..0x7FFF as a 15-bit gain). */',
            '    shinka_original[idx] = (int16_t)(((int32_t)raw_s * v->env_level) >> 15);\n'
            '    raw_s = shinka_music_sample(idx, ((uint32_t)(voice_reg(idx, 3) & ~1u) << 3) & (SPU_RAM_SIZE - 1u),\n'
            '        voice_reg(idx, 2) & 0x3fffu, raw_s, spu_ram, (non_mask & (1u << idx)) != 0);\n'
            '    /* Apply envelope (0..0x7FFF as a 15-bit gain). */')
    replace('        spu_event_record(SPU_EV_KEYON, i, v->cur_addr);',
            '        spu_event_record(SPU_EV_KEYON, i, v->cur_addr);\n'
            '        shinka_music_key_on(i, v->cur_addr, spu_ram);')
    replace('void spu_init(void) {', 'void spu_init(void) {\n    shinka_music_reset();')
    replace('    if (!out_stereo || frames <= 0) return;',
            '    if (!out_stereo || frames <= 0) return;\n'
            '    shinka_palette = shinka_music_palette_get();\n    shinka_music_block(shinka_palette);\n'
            '    const int shinka_meter_on = shinka_music_meter_active();\n'
            '    const uint32_t shinka_meter_noise = shinka_meter_on ? (uint32_t)spu_regs[reg_index(0x1F801D94u)]\n'
            '        | ((uint32_t)spu_regs[reg_index(0x1F801D96u)] << 16) : 0;')
    # Observe the actual summed dry voice bus without changing voice samples,
    # guest capture RAM, reverb sends, mixer arithmetic or main volume.
    replace('if (enabled && !any_voice && !s_shadow_tap_on) {',
            'if (enabled && !any_voice && !s_shadow_tap_on && !shinka_meter_on) {')
    replace('                    voice_l += cl;',
            '                    if (shinka_meter_on) shinka_music_meter_voice(v, cl, cr, (shinka_meter_noise & (1u << v)) != 0);\n'
            '                    voice_l += cl;')
    replace('        out_stereo[f * 2 + 0] = clamp16(mix_l);\n        out_stereo[f * 2 + 1] = clamp16(mix_r);',
            '        if (shinka_meter_on) shinka_music_meter_frame();\n'
            '        out_stereo[f * 2 + 0] = clamp16(mix_l);\n        out_stereo[f * 2 + 1] = clamp16(mix_r);')
    # The optional shadow reconstructs original ADPCM; do not let it overwrite
    # substituted voices. This project does not enable shadow audio by default.
    replace('s_shadow_tap_on = spu_shadow_enabled() ? 1 : 0;',
            's_shadow_tap_on = spu_shadow_enabled() && !shinka_palette ? 1 : 0;')
    replace('int spu_snapshot_read(const uint8_t *p, uint32_t len) {',
            'int spu_snapshot_read(const uint8_t *p, uint32_t len) {\n    shinka_music_reset();')
    replace('void spu_dma_write(uint32_t word) {',
            'void spu_dma_write(uint32_t word) {\n    shinka_music_written();')
    replace('                    spu_ram[transfer_addr]     = (uint8_t)(value & 0xFF);',
            '                    shinka_music_written();\n                    spu_ram[transfer_addr]     = (uint8_t)(value & 0xFF);')
    # Voice capture feeds guest-visible SPU RAM; preserve its canonical bytes.
    replace('if (v == 1) v1_out = s;', 'if (v == 1) v1_out = shinka_original[v];')
    replace('if (v == 3) v3_out = s;', 'if (v == 3) v3_out = shinka_original[v];')
    return code


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    text = hooks(args.source.read_text())
    if not args.output.exists() or args.output.read_text() != text:
        args.output.write_text(text, newline='\n')
