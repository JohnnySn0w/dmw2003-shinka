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

/* Panels are tiled textured rectangles, not a single menu bitmap. Expand the
 * panel/background artwork; translate glyphs and icons as intact columns.
 * This edits the host packet only. Returned width uses the renderer's separate
 * destination span, preserving the original texture rectangle and UVs. */
int shinka_menu_wide_rect(uint32_t* words, int count, int offset_x, int offset_y,
    int left, int top, int right, int bottom, int margin) {
    unsigned mode = psx_mod_read_word(0x8004b3f8u), clut;
    int x, y, w, h, anchor = 0, dest_x, dest_w = 0;
    int root = ((mode >= 0x200 && mode < 0x300) || mode == 0x1000) && shinka_menu_root_active();
    if ((!root && !shinka_menu_wide_mode(mode)) || !shinka_view_wide_active()
        || margin <= 0 || margin > 160 || count != 4 || words[0] >> 24 != 0x64
        || offset_x != 0 || (offset_y != 0 && offset_y != 256)
        || left != 0 || right != 319 || top != offset_y || bottom != top + 239) return 0;
    x = (int16_t)words[1]; y = (int16_t)(words[1] >> 16);
    w = words[3] & 65535; h = words[3] >> 16; clut = words[2] >> 16;
    if (x < -128 || x > 448 || y < -128 || y > 368 || w < 1 || w > 320 || h < 1 || h > 240) return 0;
    if (root) {
        /* The root UI has its own panel palette and resident white/yellow font
         * palettes. Field tiles, NPCs, shadows and dialogue use other palettes. */
        if (clut != 0x2697 && clut != 0x3a17 && clut != 0x3417) return 0;
        if (clut == 0x2697 && y == 13) {
            /* The instruction ribbon belongs to the right menu, including
             * its left-hand tiles. Keep its original length and overhang. */
            dest_x = x + margin;
        } else dest_x = x + (x >= 140 ? margin : -margin);
    } else if (mode == 0x1000) {
        if ((words[3] == 0x00300030 && (words[2] == 0x7da81060
                || words[2] == 0x7deb1090 || words[2] == 0x7da93000))
            || (clut == 0x7dea && y != 18)) {
            /* All three background layers and the list/description panels. */
            dest_x = stretch_x(x, margin);
            dest_w = stretch_x(x + w, margin) - dest_x;
        } else if (clut == 0x2697 && y == 13) dest_x = x + margin;
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
    } else if ((words[3] == 0x00300030 && (words[2] == 0x7ca7b850
            || words[2] == 0x7ce65828 || words[2] == 0x7ce75858))
        || (mode == 0xa00 && (clut == 0x7ba4 || clut == 0x7ba6))
        || (mode == 0xf00 && clut == 0x7eaa)) {
        /* All three scrolling background layers need the same continuous
         * transform. Treating the other two as UI columns made them jump at
         * the column boundary and drift against the correctly scaled layer. */
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
