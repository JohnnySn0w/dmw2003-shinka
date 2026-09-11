#include "menu_wide.h"
#include "view.h"
#include "mod_plugins.h"

int shinka_menu_wide_mode(unsigned mode) {
    return mode == 0xa00 || mode == 0xf00
        || (mode == 0x1000 && (shinka_menu_root_active() || shinka_menu_items_active()));
}

static int stretch_x(int x, int margin) {
    /* Floor signed coordinates so adjacent pieces share the same boundary. */
    int scaled = x * (320 + 2 * margin);
    return (scaled >= 0 ? scaled / 320 : -((-scaled + 319) / 320)) - margin;
}

static int ribbon_x(int x, int start) {
    /* The first 32px tile is the angled cap. The original ribbon starts at
     * x=34, mostly hidden behind the party. Shorten only its plain body to
     * match the visible 4:3 overhang, keeping the right edge at x=322. */
    return x <= 66 ? x + start - 34 : start + 32 + (x - 66) * (290 - start) / 256;
}

static int backdrop_tile(uint32_t* words, unsigned mode, int x, int margin) {
    if (words[3] != 0x00300030) return 0;
    int status = mode == 0x1000 || (mode >= 0x200 && mode < 0x300);
    uint32_t uv = words[2];
    if (status ? (uv != 0x7da81060 && uv != 0x7deb1090 && uv != 0x7da93000)
               : (uv != 0x7ca7b850 && uv != 0x7ce65828 && uv != 0x7ce75858)) return 0;
    /* Quantize the repeating grid's pitch once, not each moving tile's edges.
     * At 16:9 every 48px tile is 64px wide. Independently rounded edges made
     * some tiles 63px wide and changed their texel sampling as they scrolled.
     * This small backdrop-only scale rounding keeps all layers rigid, with
     * shared edges even at negative positions and across the 96px wrap. */
    int pitch = (48 * (320 + 2 * margin) + 160) / 320;
    int scaled = x * pitch;
    int dest = (scaled >= 0 ? scaled / 48 : -((-scaled + 47) / 48)) - margin;
    words[1] = (words[1] & 0xffff0000u) | (uint16_t)dest;
    return pitch;
}

/* Panels are tiled textured rectangles, not a single menu bitmap. Expand the
 * panel/background artwork; translate glyphs and icons as intact columns.
 * This edits the host packet only. Returned width uses the renderer's separate
 * destination span, preserving the original texture rectangle and UVs. */
int shinka_menu_wide_rect(uint32_t* words, int count, int offset_x, int offset_y,
    int left, int top, int right, int bottom, int margin) {
    unsigned mode = psx_mod_read_word(0x8004b3f8u), clut;
    int x, y, w, h, anchor = 0, dest_x, dest_w = 0;
    int root = ((mode >= 0x200 && mode < 0x300) || mode == 0x1000) && shinka_menu_root_active();
    int layout = root || shinka_menu_wide_mode(mode);
    int transition = (mode == 0x1000 || (mode >= 0x200 && mode < 0x300))
        && shinka_view_wide_requested();
    int backdrop = layout || (mode == 0x1000 && transition);
    unsigned op = words[0] >> 24;
    if ((!backdrop && !transition) || !shinka_view_wide_active()
        || margin <= 0 || margin > 160 || count != 4 || (op != 0x64 && op != 0x66)
        || offset_x != 0 || (offset_y != 0 && offset_y != 256)
        || left != 0 || right != 319 || top != offset_y || bottom != top + 239) return 0;
    x = (int16_t)words[1]; y = (int16_t)(words[1] >> 16);
    w = words[3] & 65535; h = words[3] >> 16; clut = words[2] >> 16;
    if (x < -128 || x > 448 || y < -128 || y > 368 || w < 1 || w > 320 || h < 1 || h > 240) return 0;
    if (op == 0x66) {
        /* The native menu wipe is five columns of animated 64px tiles, not a
         * full-screen flat rectangle. Preserve its palette animation and UVs
         * while letting the mask reach both widescreen edges. */
        if (!transition || words[3] != 0x00400040 || (words[2] & 65535) != 0x5f40
            || clut < 0x3c17 || clut > 0x3fd7 || (clut - 0x3c17) % 64
            || x < 0 || x > 256 || x % 64) return 0;
        dest_x = stretch_x(x, margin);
        words[1] = (words[1] & 0xffff0000u) | (uint16_t)dest_x;
        return stretch_x(x + w, margin) - dest_x;
    }
    if (!backdrop) return 0;
    dest_w = backdrop_tile(words, mode, x, margin);
    if (dest_w) return dest_w;
    /* During the Items/root handoff the backdrop outlives the UI tasks. Keep
     * repainting the margins through its palette fade, but don't treat a
     * half-constructed or unrelated task as the Items layout. */
    if (!layout) return 0;
    if (root) {
        /* The root UI has its own panel palette and resident white/yellow font
         * palettes. Field tiles, NPCs, shadows and dialogue use other palettes. */
        if (clut != 0x2697 && clut != 0x3a17 && clut != 0x3417
            && !(clut == 0x3817 && y >= 13 && y < 32)) return 0;
        if (clut == 0x2697 && y == 13) {
            dest_x = ribbon_x(x, 116) + margin;
            dest_w = ribbon_x(x + w, 116) + margin - dest_x;
        } else dest_x = x + (x >= 140 ? margin : -margin);
    } else if (mode == 0x1000) {
        if (clut == 0x7dea && y != 18) {
            /* List/description panels still meet their exact screen edges. */
            dest_x = stretch_x(x, margin);
            dest_w = stretch_x(x + w, margin) - dest_x;
        } else if (clut == 0x2697 && y == 13) {
            dest_x = ribbon_x(x, 144) + margin;
            dest_w = ribbon_x(x + w, 144) + margin - dest_x;
        } else if (clut == 0x3a17 && y >= 19 && y < 32 && x >= 150)
            dest_x = x + margin + 24; /* title clears the intact angled cap */
        else if (y >= 194 && w == 12 && h == 12 && (words[2] & 65535) == 0x3c54
            && clut >= 0x3057 && clut <= 0x3157 && (clut - 0x3057) % 64 == 0)
            dest_x = stretch_x(x + w, margin) - w; /* every advance-icon pulse */
        else if (y >= 194) dest_x = x - margin; /* unbroken description */
        else if (y >= 174 && y <= 187) {
            /* Selected item, equipped count, inventory count. */
            dest_x = x + (x < 154 ? -margin : x >= 230 ? margin : 0);
        } else if (clut == 0x3a17 && y >= 156 && y <= 168 && x >= 140 && x < 190)
            dest_x = x; /* whole page counter stays centered */
        else dest_x = x + ((x >= 160 || (y < 32 && x >= 150)) ? margin : -margin);
    } else if ((mode == 0xa00 && (clut == 0x7ba4 || clut == 0x7ba6))
        || (mode == 0xf00 && clut == 0x7eaa)) {
        dest_x = stretch_x(x, margin);
        dest_w = stretch_x(x + w, margin) - dest_x;
    } else {
        if (mode == 0xa00) {
            if (y >= 186 && x >= 85) anchor = 70; /* description */
            else if (x >= 140) anchor = 140; /* training choices */
        } else {
            if (y < 35 && x >= 210) anchor = 220; /* currency */
            else if (y >= 92 && y < 108) anchor = 160; /* page counter and shoulder prompt */
            else if (y >= 156) anchor = 0; /* unbroken description lines */
            else if (x >= 151) anchor = 160; /* second item/action column */
        }
        dest_x = x + stretch_x(anchor, margin) - anchor;
    }
    words[1] = (words[1] & 0xffff0000u) | (uint16_t)dest_x;
    return dest_w;
}
