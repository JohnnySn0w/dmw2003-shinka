#include "cpu_state.h"
#include "mod_plugins.h"
#include "menu_wide.h"
#include "view.h"

/* Both resident builders retain four unscaled SVECTORs on their stack.
 * Capture only axis-aligned menu scaling; world/model and rotated draws keep
 * their native path. The renderer applies the tag to its host command copy. */
static void capture(uint32_t packet, uint32_t vertices, uint32_t matrix,
    int origin_x, int origin_y, int camera_x, int camera_y) {
    if (!shinka_view_wide_requested()
        || psx_mod_read_half(matrix + 2) || psx_mod_read_half(matrix + 6)) return;
    uint32_t command[9], rect[4];
    for (int i = 0; i < 9; ++i) command[i] = psx_mod_read_word(packet + 4 + i*4);
    int x = (int16_t)psx_mod_read_half(vertices) + origin_x - camera_x;
    int y = (int16_t)psx_mod_read_half(vertices + 2) + origin_y - camera_y;
    int w = (int16_t)psx_mod_read_half(vertices + 8) - (int16_t)psx_mod_read_half(vertices);
    int h = (int16_t)psx_mod_read_half(vertices + 18) - (int16_t)psx_mod_read_half(vertices + 2);
    if (w < 1 || w > 320 || h < 1 || h > 240) return;
    rect[0] = (command[0] & 0x00ffffffu) | ((command[0] & 0x02000000u) ? 0x66000000u : 0x64000000u);
    rect[1] = (uint16_t)x | ((uint32_t)(uint16_t)y << 16);
    rect[2] = command[2]; rect[3] = w | ((uint32_t)h << 16);
    shinka_menu_animation_tag(packet + 4, command, rect, origin_x - camera_x,
        (int16_t)psx_mod_read_half(matrix));
}

void shinka_menu_sprite_quad(CPUState* cpu) {
    uint32_t sp = cpu->gpr[29], state = psx_mod_read_word(cpu->gpr[28] + 0x1c0);
    capture(cpu->gpr[21], sp + 0x20, state + 0x50,
        (int16_t)psx_mod_read_half(state + 0x30), (int16_t)psx_mod_read_half(state + 0x34),
        (int16_t)psx_mod_read_half(sp + 0x10), (int16_t)psx_mod_read_half(sp + 0x14));
}

void shinka_menu_text_quad(CPUState* cpu) {
    uint32_t sp = cpu->gpr[29], text = cpu->gpr[18];
    capture(psx_mod_read_word(sp + 0x10), sp + 0x38, text + 0xf0,
        (int16_t)psx_mod_read_half(text + 0xe0), (int16_t)psx_mod_read_half(text + 0xe4), 0, 0);
}
