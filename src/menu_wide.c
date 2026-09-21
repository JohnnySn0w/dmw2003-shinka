#include "menu_wide.h"
#include "view.h"
#include "mod_plugins.h"
#include <string.h>

/* The mode changes before the outgoing overlay stops drawing. Identify the
 * resident module too: title -> Continue briefly uses the card mode while
 * the title artwork and its fade are still alive. Never admit the intro FMV. */
int shinka_menu_boot_scene(unsigned mode) {
    if (mode != 0xe00 && mode != 0xc00 && mode != 0xc01 && mode != 0x1600 && mode != 0x2d7) return 0;
    unsigned module = psx_mod_read_word(0x80055d28u);
    if (module == 14 && mode != 0xc01) return SHINKA_BOOT_TITLE;
    if (module == 12 && (mode == 0xc00 || mode == 0xc01)) return SHINKA_BOOT_CARD;
    return 0;
}

int shinka_menu_wide_mode(unsigned mode) {
    return shinka_menu_boot_scene(mode) || mode == 0xa00 || mode == 0xf00
        || (mode == 0x1000 && shinka_menu_root_active()) || shinka_menu_status_layout();
}

static int stretch_x(int x, int margin) {
    /* Floor signed coordinates so adjacent pieces share the same boundary. */
    int scaled = x * (320 + 2 * margin);
    return (scaled >= 0 ? scaled / 320 : -((-scaled + 319) / 320)) - margin;
}

/* Stretch only the empty join between the file information and party. A
 * shared edge mapping keeps all border strips attached to both columns. */
static int card_x(int x, int margin) { return x + (x <= 144 ? -margin : margin); }

static int ribbon_x(int x, int start) {
    /* The first 32px tile is the angled cap. The original ribbon starts at
     * x=34, mostly hidden behind the party. Shorten only its plain body to
     * match the visible 4:3 overhang, keeping the right edge at x=322. */
    return x <= 66 ? x + start - 34 : start + 32 + (x - 66) * (290 - start) / 256;
}

static int folder_outline(unsigned clut, unsigned uv) {
    /* The border pulses through 16 palette rows, not different geometry.
     * Match its five texture strips so every pulse shares the panel span. */
    if (clut < 0x3c29 || clut > 0x3fe9 || (clut - 0x3c29) % 64) return 0;
    return uv == 0x0014 || uv == 0x732c || uv == 0xab00
        || uv == 0x2d88 || uv == 0xc788;
}

static int backdrop_tile(const uint32_t* words, unsigned mode) {
    if (words[3] != 0x00300030) return 0;
    uint32_t uv = words[2];
    return shinka_menu_boot_scene(mode) == SHINKA_BOOT_CARD
        ? (uv == 0x342b9200 || uv == 0x33eb9230 || uv == 0x33ab80a0)
        : mode == 0x400 ? (uv == 0x3ae91a28 || uv == 0x3b2b00a8 || uv == 0x3b6b0078)
        : mode == 0x1200 ? (uv == 0x3f6b0060 || uv == 0x3fab0030 || uv == 0x3feb0000)
        : (mode == 0xd00 || mode == 0xd01) ? (uv == 0x7d28ba30 || uv == 0x7d68bb00 || uv == 0x7d2a3814)
        : (mode == 0x1000 || (mode >= 0x200 && mode < 0x300))
            ? (uv == 0x7da81060 || uv == 0x7deb1090 || uv == 0x7da93000)
            : (mode == 0xa00 || mode == 0xf00)
                && (uv == 0x7ca7b850 || uv == 0x7ce65828 || uv == 0x7ce75858
            || (mode == 0xf00 && (uv == 0x7eea4230 || uv == 0x7f2b3400 || uv == 0x7eeb4260)));
}

/* A row repeats every 96px. Use one original packet per phase/texture and
 * repeat it into the margins at its native 48x48 size. Keeping integer guest
 * positions preserves the original diagonal motion without resampling steps.
 * Positive: output copies; negative: redundant native copy; zero: not ours. */
int shinka_menu_backdrop_positions(const uint32_t* words, int count,
    int offset_x, int offset_y, int left, int top, int right, int bottom,
    int margin, int positions[8]) {
    if (count != 4 || words[0] >> 24 != 0x64 || margin <= 0 || margin > 160
        || offset_x || (offset_y != 0 && offset_y != 256)
        || left != 0 || right != 319 || top != offset_y || bottom != top + 239
        || !shinka_view_wide_active() || !shinka_view_wide_requested()) return 0;
    unsigned mode = psx_mod_read_word(0x8004b3f8u);
    if (!backdrop_tile(words, mode)) return 0;
    int x = (int16_t)words[1], y = (int16_t)(words[1] >> 16);
    if (x < -128 || x > 448 || y < -128 || y > 368) return 0;
    if (x < 0 || x >= 96) return -1;
    while (x - 96 + 48 > -margin) x -= 96;
    int n = 0;
    for (; x < 320 + margin; x += 96) positions[n++] = x;
    return n; /* at most eight copies over the supported 640px viewport */
}

/* Panels are tiled textured rectangles, not a single menu bitmap. Expand the
 * panel/background artwork; translate glyphs and icons as intact columns.
 * This edits the host packet only. Returned width uses the renderer's separate
 * destination span, preserving the original texture rectangle and UVs. */
static int layout_rect(uint32_t* words, int count, int offset_x, int offset_y,
    int left, int top, int right, int bottom, int margin, unsigned mode, int root, int status) {
    unsigned clut;
    int x, y, w, h, anchor = 0, dest_x, dest_w = 0;
    int boot = shinka_menu_boot_scene(mode);
    int extra = status >= SHINKA_CARD_ALBUM;
    int layout = boot || root || status || mode == 0xa00 || mode == 0xf00;
    int transition = (mode == 0x1000 || mode == 0x400 || mode == 0x1200 || mode == 0xd00 || mode == 0xd01 || (mode >= 0x200 && mode < 0x300))
        && shinka_view_wide_requested();
    int backdrop = layout || transition;
    unsigned op = words[0] >> 24;
    if ((!backdrop && !transition) || !shinka_view_wide_active()
        || margin <= 0 || margin > 160 || count != 4 || (op != 0x64 && op != 0x66)
        || offset_x != 0 || (offset_y != 0 && offset_y != 256)
        || left != 0 || right != 319 || top != offset_y || bottom != top + 239) return 0;
    x = (int16_t)words[1]; y = (int16_t)(words[1] >> 16);
    w = words[3] & 65535; h = words[3] >> 16; clut = words[2] >> 16;
    if (x < -128 || x > 448 || y < -128 || y > 368 || w < 1 || w > 320 || h < 1 || h > 240) return 0;
    if (!boot && op == 0x66 && (!extra || words[3] == 0x00400040)) {
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
    if (backdrop_tile(words, mode)) return 0; /* repeated at native size by GPU */
    /* During the Items/root handoff the backdrop outlives the UI tasks. Keep
     * repainting the margins through its palette fade, but don't treat a
     * half-constructed or unrelated task as the Items layout. */
    if (!layout) return 0;
    if (boot == SHINKA_BOOT_TITLE) {
        /* Five strips form one circuit-board image (different texture pages).
         * Only that image widens; choices, copyright and either logo stay
         * centered at their native size. Shared edges avoid visible seams. */
        if (op != 0x64 || words[3] != 0x00f00040 || y != 0
            || x < 0 || x > 256 || x % 64
            || (words[2] != 0x7cc00000 && words[2] != 0x7cc00040
                && words[2] != 0x7d000000 && words[2] != 0x7d000040)) return 0;
        dest_x = stretch_x(x, margin);
        dest_w = stretch_x(x+w, margin)-dest_x;
    } else if (boot == SHINKA_BOOT_CARD) {
        unsigned uv = words[2] & 65535;
        /* Widen the enclosing sheet, keeping the file information and party
         * as intact left/right groups. The bottom instruction is a single
         * sentence: it must never split at the screen's midpoint. */
        if (clut == 0x34ab) {
            if (h == 146 || (h == 4 && (y == 116 || y == 181 || y == 188 || y == 221))
                || (y == 100 && h == 4)) {
                dest_x = card_x(x, margin);
                dest_w = card_x(x+w, margin)-dest_x;
            } else dest_x = x + (x >= 147 ? margin : -margin);
        } else if (clut == 0x332b && uv == 0x34c0) {
            dest_x = card_x(x, margin);
            dest_w = card_x(x+w, margin)-dest_x;
        } else if (clut == 0x39eb || clut == 0x336b || clut == 0x32eb)
            dest_x = x-margin; /* pillar, title cap and its two connectors */
        else if (y < 89) dest_x = x+margin; /* card sockets and all pulse palettes */
        else if (clut == 0x32ab || (w == 12 && h == 12 && uv == 0x3c54
            && clut >= 0x3057 && clut <= 0x3157 && (clut-0x3057)%64 == 0))
            dest_x = x+margin; /* confirmation box / every advance-icon pulse */
        else if (clut == 0x3a17 && y >= 109 && y < 185)
            dest_x = x-margin; /* access/error messages span the whole sheet */
        else if (y >= 185) dest_x = x + (x >= 188 && (y == 189 || y == 190 || y == 203 || y == 204) ? margin : -margin);
        else dest_x = x + (x >= 147 ? margin : -margin);
    } else if (extra) {
        if (status == SHINKA_FIELD_INN) {
            /* Location stays left; money, price, choices and highlight form
             * right-anchored groups. World sprites and speech use other CLUTs. */
            if (clut != 0x2bd7 && clut != 0x2697 && clut != 0x3a17 && clut != 0x3417) return 0;
            dest_x = x + (y < 36 && x < 160 ? -margin : margin);
        } else if (status == SHINKA_LAB_CHART) {
            /* Preserve the chart's node/line geometry as one centered unit.
             * Its title, page indicator and shoulder prompts use the edges. */
            dest_x = x;
            if (y < 47) {
                /* Identify the two ribbons by their texture strips so each
                 * cap stays attached to its own header during animation. */
                unsigned uv = words[2] & 65535;
                int page = clut == 0x7cab ? (uv == 0x59ec || uv == 0x3594) : x >= 240;
                dest_x += page ? margin : -margin;
            } else if ((clut == 0x3a17 && y == 196 && (x <= 47 || x >= 278))
                || (clut >= 0x7d29 && clut <= 0x7de9 && (clut-0x7d29)%64 == 0
                    && y == 201 && ((words[2] & 65535) == 0x5868 || (words[2] & 65535) == 0xed00)))
                dest_x += x >= 200 ? margin : -margin;
        } else if (status == SHINKA_LAB_LOAD) {
            if (clut == 0x7cab && y == 191) {
                dest_x = stretch_x(x, margin);
                dest_w = stretch_x(x+w, margin)-dest_x;
            } else if (y >= 191) dest_x = x + (y >= 208 && x >= 265 ? margin : -margin);
            else dest_x = x + ((y >= 65 || x >= 140) ? margin : -margin);
        } else if (status == SHINKA_LAB || status == SHINKA_LAB_TECHNIQUES) {
            /* The complete form detail sheet keeps its native width and
             * moves to the right edge: stats, divider, skills and header. */
            dest_x = x + (status == SHINKA_LAB_TECHNIQUES && y >= 100
                ? margin : x >= 140 ? margin : -margin);
        } else if (status == SHINKA_CARD_ALBUM) {
            if (y >= 50 && y < 150) {
                int col = (x - 32) / 42;
                if (col < 0) col = 0;
                if (col > 5) col = 5;
                dest_x = x + (2*col - 5)*margin/5;
            } else if (clut == 0x3deb && y >= 154 && x >= 74) {
                dest_x = stretch_x(x, margin);
                dest_w = stretch_x(x+w, margin)-dest_x;
            } else {
                anchor = y < 50 ? (x < 190 ? 0 : 320)
                    : x >= 259 ? 320 : y >= 179 ? 74 : x >= 130 ? 130 : 0;
                dest_x = x + stretch_x(anchor, margin)-anchor;
            }
        } else if (status == SHINKA_FOLDER_CARDS) {
            /* The card picker is a list, not nine independently placed grid
             * columns. Its frame, text, cursor and descriptions move as one. */
            dest_x = x;
        } else { /* Folder selection / editing / card sorting. */
            int grid = status == SHINKA_FOLDER_EDIT || status == SHINKA_FOLDER_EXPLAIN;
            if (status == SHINKA_FOLDER_EXPLAIN && clut == 0x3a6a) {
                dest_x = stretch_x(x, margin);
                dest_w = stretch_x(x+w, margin)-dest_x;
            } else if (status == SHINKA_FOLDER_EXPLAIN && clut == 0x3a17 && y >= 23 && y < 40 && x >= 74)
                dest_x = x + stretch_x(74, margin)-74;
            else if (status == SHINKA_FOLDER_EXPLAIN && clut == 0x3aab && y == 36)
                dest_x = x + stretch_x(259, margin)-259;
            else if (clut == 0x39a8 && y == 28) dest_x = x + margin;
            else if (grid && y >= 56)
                dest_x = x; /* compact cards, cursor and last-row help panel */
            else if (grid && clut == 0x3a17 && y >= 23 && y <= 24 && x < 140)
                dest_x = x + stretch_x(22, margin)-22 + 4;
            else if (clut == 0x3a68 || clut == 0x3de9
                || (status == SHINKA_FOLDER_SELECT && folder_outline(clut, words[2] & 65535))) {
                dest_x = stretch_x(x, margin);
                dest_w = stretch_x(x+w, margin)-dest_x;
            } else if (status == SHINKA_FOLDER_SELECT && clut == 0x3a17
                && y >= 83 && y <= 175 && (y-83)%45 <= 1) {
                /* Folder names keep a native-size inset from the expanded frame. */
                dest_x = x + stretch_x(29, margin)-29 + 4;
            } else if ((status == SHINKA_FOLDER_SELECT && y >= 99 && ((y-99)%45) <= 2)
                || (grid && y >= 40 && y <= 41)) {
                int start = grid ? 22 : 29;
                int group = (x-start)/35;
                if (group < 0) group = 0;
                if (group > 5) group = 5;
                anchor = start+group*35;
                dest_x = x + stretch_x(anchor, margin)-anchor;
            } else dest_x = x + (x >= 140 ? margin : -margin);
        }
    } else if ((root || (status && status != SHINKA_STATUS_MAP)) && clut == 0x2697 && y == 13) {
        /* Party selection inside character Status reuses the Start/Items
         * ribbon, not the taller detail-page header. Transform every strip
         * together before any page's left/right column anchoring. */
        int start = root ? 116 : 144;
        dest_x = ribbon_x(x, start) + margin;
        dest_w = ribbon_x(x + w, start) + margin - dest_x;
    } else if (root) {
        /* The root UI has its own panel palette and resident white/yellow font
         * palettes. Field tiles, NPCs, shadows and dialogue use other palettes. */
        if (clut != 0x2697 && clut != 0x3a17 && clut != 0x3417
            && !(clut == 0x3817 && y >= 13 && y < 32)) return 0;
        dest_x = x + (x >= 140 ? margin : -margin);
    } else if (status == SHINKA_STATUS_MAP) {
        if (clut == 0x7e2b || clut == 0x3a17 || clut == 0x3417) {
            /* The location/travel tooltip is screen-relative. Keep its text
             * and all border strips together at their original left inset. */
            dest_x = x - margin;
        } else {
            /* Native map artwork is 392px wide. At 16:9 it fits without
             * stretching. Undo the guest's 0..-72 horizontal camera pan for
             * artwork, icons, selection pulses and free cursor alike. The
             * guest still owns snapping, visitation and travel eligibility.
             * Smaller margins reveal proportionally more of the map. */
            int reveal = margin < 36 ? margin : 36;
            dest_x = x - shinka_menu_map_pan() * reveal / 36 - reveal;
        }
    } else if (status >= SHINKA_STATUS_CHARACTER && status <= SHINKA_STATUS_CHARACTER_TECHNIQUES) {
        int techniques = status == SHINKA_STATUS_CHARACTER_TECHNIQUES;
        int digivolve = status == SHINKA_STATUS_DIGIVOLVE || techniques;
        int form_y = techniques ? 63 : 97;
        int footer = y >= 194 && (status == SHINKA_STATUS_EQUIPMENT
            || status == SHINKA_STATUS_CHARACTER_SELECT || techniques);
        if (clut == 0x7dea && y == 13) {
            /* This header has a 44px leading tile, unlike the Start ribbon.
             * Keep its body beside the party instead of exposing its long
             * formerly occluded tail across the middle of the wide screen. */
            dest_x = x <= 64 ? x + 124 + margin : 188 + margin + (x - 64) * 164 / 288;
            int end = x + w;
            dest_w = (end <= 64 ? end + 124 + margin : 188 + margin + (end - 64) * 164 / 288) - dest_x;
        } else if (clut == 0x3a17 && x >= 150 && y >= 19
            && y < (status == SHINKA_STATUS_CHARACTER ? 46 : 32))
            dest_x = x + margin + 24; /* Both action rows and cursor clear the cap. */
        else if (clut == 0x7dea && y == 194 && (!digivolve || techniques)) {
            dest_x = stretch_x(x, margin);
            dest_w = stretch_x(x + w, margin) - dest_x;
        } else if (digivolve && y >= form_y && !footer) {
            /* Keep the whole stats/skills sheet compact at the right edge.
             * Expanding only its fill still leaves an oversized skill list. */
            dest_x = x + margin;
        } else if (techniques && clut == 0x3a17 && y == 212 && x >= 266)
            dest_x = x + stretch_x(303, margin) - 303;
        else if (footer) dest_x = x - margin;
        else if (status == SHINKA_STATUS_EQUIPMENT)
            dest_x = x + ((x >= 148 || (y >= 54 && x >= 112)) ? margin : -margin);
        else if (digivolve && ((clut == 0x7de9 && y == form_y-29)
            || (clut == 0x3a17 && y >= form_y-20 && y <= form_y-19)))
            dest_x = x + margin; /* Base-partner tab belongs to the form list. */
        else if (digivolve)
            dest_x = x + ((x >= 160 || (y < 37 && x >= 148)) ? margin : -margin);
        else dest_x = x + (x >= 148 ? margin : -margin);
    } else if (mode == 0x1000) {
        if (clut == 0x7dea && y != 18 && (status != SHINKA_STATUS_TECHNIQUES || y >= 194)
            && (status != SHINKA_STATUS_FOLDERS || y >= 194)) {
            /* List/description panels still meet their exact screen edges. */
            dest_x = stretch_x(x, margin);
            dest_w = stretch_x(x + w, margin) - dest_x;
        } else if (clut == 0x3a17 && y >= 19 && y < 32 && x >= 150)
            dest_x = x + margin + 24; /* title clears the intact angled cap */
        else if (y >= 194 && w == 12 && h == 12 && (words[2] & 65535) == 0x3c54
            && clut >= 0x3057 && clut <= 0x3157 && (clut - 0x3057) % 64 == 0)
            dest_x = stretch_x(x + w, margin) - w; /* every advance-icon pulse */
        else if (status == SHINKA_STATUS_TECHNIQUES && clut == 0x3a17
            && y == 212 && x >= 266)
            dest_x = x + stretch_x(303, margin) - 303; /* MP block retains its inset from the inner border */
        else if (y >= 194) dest_x = x - margin; /* unbroken description */
        else if (status == SHINKA_STATUS_SORT) dest_x = x - margin;
        else if (status == SHINKA_STATUS_TECHNIQUES)
            dest_x = x + (x >= 148 ? margin : -margin); /* list tab, frame, text and cursor together */
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

int shinka_menu_wide_rect(uint32_t* words, int count, int offset_x, int offset_y,
    int left, int top, int right, int bottom, int margin) {
    unsigned mode = psx_mod_read_word(0x8004b3f8u);
    int root = ((mode >= 0x200 && mode < 0x300) || mode == 0x1000) && shinka_menu_root_active();
    return layout_rect(words, count, offset_x, offset_y, left, top, right, bottom,
        margin, mode, root, root ? 0 : shinka_menu_status_layout());
}

/* Animated menus use POLY_FT4 instead of SPRT. Record the unscaled rectangle
 * while the native builder still has it; classifying the shrunken coordinates
 * would send pieces to different columns. Tags describe transient commands,
 * never modify guest RAM, and are checked against all nine submitted words.
 * The two packet buffers coexist, so do not clear tags on every present. */
typedef struct {
    uint32_t source, command[9], rect[4], mode;
    int pivot, scale, root, status;
} MenuAnimation;
static MenuAnimation animations[4096];
/* Direct packet-word lookup avoids hash collisions between the two frame
 * buffers. The bounded ring owns at most 4096 recently built commands. */
static uint16_t animation_index[0x200000 / 4];
static unsigned animation_next;

void shinka_menu_animation_reset(void) {
    memset(animation_index, 0, sizeof(animation_index));
    memset(animations, 0, sizeof(animations)); animation_next = 0;
}

void shinka_menu_animation_tag(uint32_t source, const uint32_t* command,
    const uint32_t* rect, int pivot, int scale) {
    unsigned mode = psx_mod_read_word(0x8004b3f8u);
    if (!shinka_view_wide_requested() || (command[0] >> 24 != 0x2c && command[0] >> 24 != 0x2e)
        || scale < 0 || scale > 4096 || pivot < -128 || pivot > 448) return;
    source &= 0x1fffffu;
    if (!source || (source & 3)) return;
    unsigned slot = animation_index[source >> 2];
    if (!slot) {
        slot = animation_next++ % 4096 + 1;
        uint32_t previous = animations[slot - 1].source;
        if (previous && animation_index[previous >> 2] == slot) animation_index[previous >> 2] = 0;
        animation_index[source >> 2] = (uint16_t)slot;
    }
    MenuAnimation* a = &animations[slot - 1];
    a->source = source; a->mode = mode; a->pivot = pivot; a->scale = scale;
    a->root = shinka_menu_root_active();
    a->status = a->root ? 0 : shinka_menu_status_layout();
    memcpy(a->command, command, sizeof(a->command));
    memcpy(a->rect, rect, sizeof(a->rect));
}

static int scaled_x(int x, int scale) {
    int n = x * scale;
    return n >= 0 ? n / 4096 : -((-n + 4095) / 4096);
}

void shinka_menu_wide_quad(uint32_t* words, int count, uint32_t source,
    int offset_x, int offset_y, int left, int top, int right, int bottom, int margin) {
    if ((count != 9 && count != 5 && count != 6 && count != 8) || !shinka_view_wide_active() || margin <= 0 || margin > 160
        || offset_x || (offset_y != 0 && offset_y != 256)
        || left || right != 319 || top != offset_y || bottom != top + 239) return;
    if (count == 8) {
        /* Transfer fill is an untextured Gouraud quad, separate from its
         * textured frame. Keep the acknowledged-byte animation intact. */
        if (shinka_menu_boot_scene(psx_mod_read_word(0x8004b3f8u)) != SHINKA_BOOT_CARD
            || words[0] >> 24 != 0x38 || words[1] != 0x00c100cdu
            || words[5] != 0x00cb00cdu || (words[3] >> 16) != 193
            || (words[7] >> 16) != 203 || (uint16_t)words[3] != (uint16_t)words[7]
            || (uint16_t)words[3] < 205 || (uint16_t)words[3] > 303) return;
        for (int i = 1; i < 8; i += 2)
            words[i] = (words[i] & 0xffff0000u) | (uint16_t)((int16_t)words[i]+margin);
        return;
    }
    if (count == 6) {
        /* Native title/card screen fades are a four-triangle fan. Move only
         * its outer corners, preserving the center and per-vertex intensity. */
        if (!shinka_menu_boot_scene(psx_mod_read_word(0x8004b3f8u))
            || words[0] >> 24 != 0x32 || words[1] != 0x007800a0) return;
        for (int i = 3; i <= 5; i += 2) {
            int x = (int16_t)words[i], y = (int16_t)(words[i] >> 16);
            if ((x != 0 && x != 320) || (y != -15 && y != 260)) return;
        }
        for (int i = 3; i <= 5; i += 2)
            words[i] = (words[i] & 0xffff0000u) | (uint16_t)((int16_t)words[i] == 0 ? -margin : 320+margin);
        return;
    }
    if (count == 5) {
        unsigned mode = psx_mod_read_word(0x8004b3f8u);
        /* The shop/card overlay fades with a full-screen semitransparent
         * POLY_F4. Keep the fade covering the same width as its panels. */
        if (words[0] >> 24 != 0x2a || words[1] || words[2] != 320
            || words[3] != 0x01000000u || words[4] != 0x01000140u
            || (mode != 0x1000 && mode != 0x400 && mode != 0x1200
                && mode != 0xd00 && mode != 0xd01 && mode != 0xa00 && mode != 0xf00
                && !shinka_menu_boot_scene(mode))) return;
        for (int i = 1; i <= 4; ++i)
            words[i] = (words[i] & 0xffff0000u) | (uint16_t)(i & 1 ? -margin : 320 + margin);
        return;
    }
    source &= 0x1fffffu;
    unsigned slot = animation_index[source >> 2];
    if (!slot) return;
    MenuAnimation* a = &animations[slot - 1];
    if (!source || a->source != source || a->mode != psx_mod_read_word(0x8004b3f8u)
        || memcmp(a->command, words, sizeof(a->command))) return;
    uint32_t rect[4]; memcpy(rect, a->rect, sizeof(rect));
    int width = layout_rect(rect, 4, offset_x, offset_y, left, top, right, bottom,
        margin, a->mode, a->root, a->status);
    if (!width && rect[1] == a->rect[1]) return;
    int original = (int16_t)a->rect[1], w = a->rect[3] & 65535;
    int dest = (int16_t)rect[1];
    if (!width) width = w;
    int ribbon = (a->rect[1] >> 16) == 13 && (a->rect[2] >> 16 == 0x2697 || a->rect[2] >> 16 == 0x7dea);
    /* Edge-driven panels share ONE pivot across all their strips, glyphs and
     * icons, even when some move left and others move right in the wide layout.
     * Translating the pivot separately per strip splits the panel by as much
     * as two margins during its collapse. Portraits with their own interior
     * pivot still scale around their translated centre. */
    int edge = a->pivot == 0 || a->pivot == 320;
    int pivot = !edge && width == w && !ribbon
        ? a->pivot + dest - original : stretch_x(a->pivot, margin);
    for (int i = 0; i < 4; ++i) {
        int old_x = original + (i & 1 ? w : 0);
        int new_x = dest + (i & 1 ? width : 0);
        /* Apply the same native fixed-point animation around the wide pivot.
         * A delta retains the guest's rounding and any vertical motion. */
        int dx = pivot - a->pivot + scaled_x(new_x - pivot, a->scale)
            - scaled_x(old_x - a->pivot, a->scale);
        unsigned pos = 1 + i*2;
        words[pos] = (words[pos] & 0xffff0000u) | (uint16_t)((int16_t)words[pos] + dx);
    }
}
