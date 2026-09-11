/* The six original row slots remain in place. Two additional text tasks live
 * after all original children, so cursor/party offsets and old states survive. */
#include <stdio.h>
extern void shinka_rates_get(int*, int*, int*);
extern int shinka_rates_set(int, int, int);
extern int shinka_encounter_rate_get(void);
extern int shinka_encounter_rate_set(int);
extern int shinka_music_palette_get(void);
extern int shinka_music_palette_set(int);
extern int shinka_music_available(void);
extern int shinka_view_get(int);
extern int shinka_view_set(int, int);
extern int shinka_motion_get(int);
extern int shinka_motion_set(int, int);
extern void shinka_rewards_refresh(void);
extern void shinka_rewards_tick(void);
extern void shinka_rewards_activate(void);
static uint32_t text_scratch;
static uint32_t panel_scratch;

static int expanded(uint32_t p) {
    return object(p, QUICK_MENU) && READ(p + 0x20) == 0x2d;
}

static int motion_index(int percent) {
    return percent == 200 ? 3 : percent == 150 ? 2 : percent == 125 ? 1 : 0;
}

static int short_settings(uint32_t page) { return page == 4 || page == 6; }

static uint32_t rate_tag(int battle, int dv, int fixed) {
    return (uint32_t)((battle << 8) | (dv << 12) | (fixed ? 0x10000 : 0)
        | ((shinka_encounter_rate_get() / 50 + 1) << 20)
        | (shinka_music_palette_get() << 24)
        | (shinka_view_get(0) << 26) | (shinka_view_get(1) << 27)
        | (shinka_view_get(2) << 19)
        | (motion_index(shinka_motion_get(0)) << 17) | (motion_index(shinka_motion_get(1)) << 29));
}

uint32_t shinka_menu_slot(uint32_t p, uint32_t address) {
    uint32_t children = READ(p + 0x24);
    if (expanded(p) && address >= children + 0x24 && address <= children + 0x28)
        return address + 0x88; /* rows 6/7 -> 0xac/0xb0 */
    return address;
}

void shinka_menu_allocate(CPUState* cpu) {
    uint32_t mode = READ(MODE);
    if (enabled && READ(0x8005cca8) == 2 && ((mode >> 8) == 2 || mode == STATUS)
        && cpu->gpr[4] == QUICK_MENU && cpu->gpr[5] == 0xa0 && cpu->gpr[6] == 0xac) {
        cpu->gpr[5] = 0xa8; /* +a0 page, +a4 persistence error; zeroed by allocator */
        cpu->gpr[6] = 0xb4;
    }
}

void shinka_menu_construct(CPUState* cpu) {
    uint32_t p = cpu->gpr[4];
    if (!expanded(p)) return;
    WRITE(p + 0xa0, 0); WRITE(p + 0xa4, 0);
    WRITE(p + 0x5c, 7 + (READ(p + 0x60) != 0));
    if (READ(p + 0x58) >= READ(p + 0x5c)) WRITE(p + 0x58, 0);
}

void shinka_menu_task_ready(CPUState* cpu) {
    uint32_t p = cpu->gpr[4];
    /* Called after the resident task-advance method clears substates, before
     * it increments lifecycle 0 -> 1. The Status controller's substate 1
     * creates its root list; substate 0 would dispatch a stock submenu. */
    if (READ(MODE) != STATUS || READ(0x8004b400) != JOURNAL
        || READ(0x8004b404) != LAB_ROOT_RETURN
        || !object(p, 0x80099894) || READ(p + 0xc) != 0
        || (READ(p + 0x20) != 2 && READ(p + 0x20) != 3)) return;
    WRITE(p + 0x10, 1);
    WRITE(0x8005ccf0, enabled && READ(0x8005cca8) == 2
        ? 5 + (psx_mod_read_byte(0x80048f42) != 0) : 4);
    WRITE(0x8004b404, 0); /* consumed once; all return state lives in guest RAM */
}

static uint32_t encode(const char* text) {
    uint32_t out;
    if (!text_scratch || READ(text_scratch) != 0x53484d55) {
        text_scratch = psx_mod_alloc_guest_memory(256, 4);
        if (!text_scratch) return 0;
        WRITE(text_scratch, 0x53484d55);
    }
    out = text_scratch + 4;
    while (*text && out < text_scratch + 250) {
        unsigned char c = (unsigned char)*text++;
        if (c >= '0' && c <= '9') {
            psx_mod_write_byte(out++, c - '0' + 4);
        } else if (c == ' ' || c == ':' || c == '%') {
            psx_mod_write_byte(out++, 1);
            psx_mod_write_byte(out++, c == ' ' ? 1 : c == ':' ? 7 : 0x2a);
        } else {
            psx_mod_write_byte(out++, c >= 'a' && c <= 'z' ? c - 57 : c - 51);
        }
    }
    psx_mod_write_byte(out, 0);
    return text_scratch + 4;
}

void shinka_menu_text(CPUState* cpu) {
    uint32_t p = cpu->gpr[17], row;
    const char* label = NULL;
    char value[64];
    static const char* labels[] = {"ITEMS", "SORT", "MAP", "TECHNIQUES", "STATUS", "CARD FOLDERS", "DIGIVOLUTIONS", "SETTINGS"};
    if (!expanded(p)) return;
    if (cpu->gpr[31] == 0x8001288c) {
        label = READ(p + 0xa4) & 1 ? "Settings save failed" : READ(p + 0xa0) == 4
            ? "Actions: Attacks and reactions" : READ(p + 0xa0) == 6
            ? "Field test: Blank edges" : READ(p + 0xa0) == 1
            ? (shinka_music_palette_get() && !shinka_music_available() ? "Music pack missing" : "SETTINGS: Left Right")
            : NULL; /* retain the stock hint, including its colored button glyph */
    } else if (cpu->gpr[31] == 0x80012938) {
        row = READ(p + 0x18);
        if (row >= 8) return;
        if (READ(p + 0xa0) == 6) {
            int battle, dv, fixed;
            shinka_rates_get(&battle, &dv, &fixed);
            if (!row) WRITE(p + 0xa4, (READ(p + 0xa4) & 1) | rate_tag(battle, dv, fixed));
            label = row == 0 ? (shinka_view_get(0) ? "Battle: 16:9" : "Battle: 4:3")
                : row == 1 ? (shinka_view_get(2) ? "Field: 16:9 test" : "Field: 4:3")
                : row == 2 ? "BACK" : "";
        } else if (READ(p + 0xa0) == 4) {
            int battle, dv, fixed;
            shinka_rates_get(&battle, &dv, &fixed);
            if (!row) WRITE(p + 0xa4, (READ(p + 0xa4) & 1) | rate_tag(battle, dv, fixed));
            if (row < 2) {
                snprintf(value, sizeof(value), "%s poses: %d%%", row ? "Action" : "Idle", shinka_motion_get(row));
                label = value;
            } else label = row == 2 ? "BACK" : "";
        } else if (READ(p + 0xa0) == 1) {
            int battle, dv, fixed;
            shinka_rates_get(&battle, &dv, &fixed);
            if (row == 0) {
                WRITE(p + 0xa4, (READ(p + 0xa4) & 1) | rate_tag(battle, dv, fixed));
                snprintf(value, sizeof(value), "EXP: %dx", battle); label = value;
            }
            else if (row == 1) {
                snprintf(value, sizeof(value), fixed ? "DV EXP: %d pts" : "DV EXP: %dx", fixed ? fixed : dv);
                label = value;
            } else if (row == 2) {
                snprintf(value, sizeof(value), "Encounters: %d%%", shinka_encounter_rate_get()); label = value;
            } else if (row == 3) {
                static const char* palettes[] = {"Original", "DS", "Sampled", "Chip"};
                int palette = shinka_music_palette_get();
                snprintf(value, sizeof(value), "Soundtrack: %s", palettes[palette >= 0 && palette < 4 ? palette : 0]);
                label = value;
            } else if (row == 4) {
                label = "Screen view";
            } else if (row == 5) {
                snprintf(value, sizeof(value), "Battle zoom: %d%%", 100 - shinka_view_get(1) * 10);
                label = value;
            } else label = row == 6 ? "Battle motion" : "BACK";
        } else label = !enabled && row >= 5 + (READ(p + 0x60) != 0) ? ""
            : labels[row + (row >= 5 && !READ(p + 0x60))];
    }
    if (label) {
        uint32_t string = encode(label);
        if (string) { cpu->gpr[5] = string; cpu->gpr[6] = 0xffffffff; }
    }
}

void shinka_menu_background(CPUState* cpu) {
    uint32_t p = cpu->gpr[17], source, textures, out, rows, x, y, i;
    if (cpu->gpr[31] != 0x80013108 || !expanded(p)) return;
    source = cpu->gpr[4];
    if (source < 0x80090000 || source > 0x801f0000 || READ(source) != 384) return;
    textures = source + 384 + 56 * 14;
    /* Six original panel tiles: top/middle/bottom, left/interior. Preserve
     * their pixels and add complete 14-pixel rows, including separators. */
    for (i = 0; i < 6; ++i)
        if (psx_mod_read_half(textures + i * 14 + 4) != 40
            || psx_mod_read_half(textures + i * 14 + 6) != (i < 2 ? 22 : i < 4 ? 14 : 20)) return;
    if (!panel_scratch || READ(panel_scratch + 508) != 0x4d454e55) {
        panel_scratch = psx_mod_alloc_guest_memory(512, 4);
        if (!panel_scratch) return;
        WRITE(panel_scratch + 508, 0x4d454e55);
    }
    WRITE(panel_scratch, 16); WRITE(panel_scratch + 4, 100); WRITE(panel_scratch + 8, 104);
    psx_mod_write_byte(panel_scratch + 100, 0); /* one sprite, id zero */
    for (i = 0; i < 84; ++i) psx_mod_write_byte(panel_scratch + 16 + i, psx_mod_read_byte(textures + i));
    rows = short_settings(READ(p + 0xa0)) ? 3 : READ(p + 0xa0) == 1 ? 8
        : (enabled ? 7 : 5) + (READ(p + 0x60) != 0);
    psx_mod_write_half(panel_scratch + 104, (uint16_t)(rows * 4));
    psx_mod_write_half(panel_scratch + 106, 0);
    psx_mod_write_half(panel_scratch + 108, 0xffff);
    out = panel_scratch + 110;
    for (y = 0; y < rows; ++y) for (x = 0; x < 4; ++x) {
        unsigned tile = (y == 0 ? 0 : y == rows - 1 ? 4 : 2) + (x != 0);
        psx_mod_write_half(out, (uint16_t)tile);
        psx_mod_write_half(out + 2, (uint16_t)(x * 40));
        psx_mod_write_half(out + 4, (uint16_t)(y ? 22 + (y - 1) * 14 : 0));
        out += 6;
    }
    cpu->gpr[4] = panel_scratch; cpu->gpr[5] = 0;
}

static uint16_t button(unsigned logical) {
    unsigned bit = psx_mod_read_byte(0x8004b874 + logical);
    return bit < 16 ? (uint16_t)(1u << bit) : 0;
}

static void refresh_menu(uint32_t p, unsigned page, unsigned selection) {
    uint32_t children = READ(p + 0x24), cursor = READ(children + 0x24);
    WRITE(p + 0xa0, page); WRITE(p + 0x58, selection);
    WRITE(p + 0x10, 0); /* rerun original text setters, retaining the open panels */
    /* Rebuild all labels, including blanks, before reducing the input count
     * for the smaller settings pages. This clears text from the previous page. */
    WRITE(p + 0x5c, page == 1 || short_settings(page) ? 8 : 7 + (READ(p + 0x60) != 0));
    if (object(cursor, 0x8001b0a4)) {
        WRITE(cursor + 0x58, 176); WRITE(cursor + 0x5c, 49 + 14 * selection);
        WRITE(cursor + 0x68, 1); /* request the stock cursor's position update */
    }
    psx_mod_write_half(0x8004b818, 0);
}

static int legacy_root_hint(uint32_t p) {
    /* Old savestates own a copied, already-rendered string: the text setter
     * hook cannot repair it until the native menu rebuilds its labels.
     * Follow only the ribbon child and match our two retired English hints. */
    static const unsigned char prefix[] = {
        0x21,0x39,0x30,0x28,0x35,0x2e,0x33,0x2c,0x01,0x07,
        0x01,0x01,0x10,0x33,0x36,0x3a,0x2c,0x01,0x01
    }; /* "Triangle: Close " in the game's encoding */
    static const unsigned char status[] = {0x20,0x3b,0x28,0x3b,0x3c,0x3a,0};
    static const unsigned char menu[] = {0x1a,0x2c,0x35,0x3c,0};
    uint32_t children = READ(p + 0x24), header, text;
    const unsigned char* suffix;
    unsigned length, i;
    if (children < 0x80090000u || children > 0x801ffffcu || (children & 3)) return 0;
    header = READ(children);
    if (!object(header, 0x8001ac14) || READ(header + 0x114) != 0x800194e8) return 0;
    length = psx_mod_read_half(header + 0x62);
    if (length != 25 && length != 23) return 0;
    text = READ(header + 0x5c);
    if (text < 0x80090000u || text > 0x80200000u - length - 1) return 0;
    for (i = 0; i < sizeof(prefix); ++i)
        if (psx_mod_read_byte(text + i) != prefix[i]) return 0;
    suffix = length == 25 ? status : menu;
    for (; i <= length; ++i)
        if (psx_mod_read_byte(text + i) != suffix[i - sizeof(prefix)]) return 0;
    return 1;
}

void shinka_journal_quick_menu(CPUState* cpu) {
    uint32_t p = cpu->gpr[4], row, count;
    uint16_t pressed;
    if (!expanded(p) || READ(0x8004b3fc)) return;
    wide_menu_root = p; wide_menu_mode = READ(MODE);
    if (READ(MODE) == STATUS && READ(p + 0xa0) == 5) return; /* map's stock close path */
    if (READ(MODE) == STATUS && READ(p + 0xc) == 1 && READ(p + 0x10) == 4
        && READ(p + 0x14) == 1 && READ(p + 0xa0) == 0
        && READ(p + 0x58) == 5 + (READ(p + 0x60) != 0)) {
        /* Mark only after stock input has accepted confirm. Navigation has
         * priority in the original handler, including held-key repetition. */
        WRITE(p + 0xa0, 3);
    }
    if (READ(MODE) == STATUS && READ(p + 0xa0) == 3) {
        /* Confirm normally destroys this root and sends its index to the
         * stock six-entry submenu table. Close the entire Status overlay
         * instead; the resident transition hook selects the journal. */
        WRITE(p + 0x14, 0);
        WRITE(0x8005ccf0, 4);
        return;
    }
    if (READ(p + 0xc) != 1) return;
    if (enabled && !READ(p + 0xa0) && READ(p + 0x10) == 3 && legacy_root_hint(p)) {
        refresh_menu(p, 0, READ(p + 0x58));
        return;
    }
    count = 7 + (READ(p + 0x60) != 0);
    if (!enabled) {
        /* A save made with this layout still owns the appended children.
         * Keep safe addressing/teardown, but do not expose disabled actions. */
        if (READ(p + 0xa0) != 2 && READ(p + 0x10) == 3)
            refresh_menu(p, 2, READ(p + 0x58) < count - 2 ? READ(p + 0x58) : 4);
        WRITE(p + 0x5c, READ(p + 0x10) == 3 ? count - 2 : count);
        return;
    }
    if (READ(p + 0xa0) == 1 && READ(p + 0x10) == 3
        && READ(p + 0x5c) >= 4 && READ(p + 0x5c) < 8) {
        /* Old settings states retain BACK instead of entering a new submenu. */
        refresh_menu(p, 1, READ(p + 0x58) == READ(p + 0x5c) - 1 ? 7 : READ(p + 0x58));
        return;
    }
    WRITE(p + 0x5c, READ(p + 0x10) == 3
        ? (short_settings(READ(p + 0xa0)) ? 3 : READ(p + 0xa0) == 1 ? 8 : count)
        : (READ(p + 0xa0) == 1 || short_settings(READ(p + 0xa0)) ? 8 : count));
    if (READ(p + 0x10) != 3) return;
    if (READ(p + 0xa0) > 1 && !short_settings(READ(p + 0xa0))) { refresh_menu(p, 0, 4); return; }
    pressed = psx_mod_read_half(0x8004b818);
    row = READ(p + 0x58);
    if (!READ(p + 0xa0)) {
        if (row == count - 1 && (pressed & button(13))) refresh_menu(p, 1, 0);
        return;
    }
    {
        int battle, dv, fixed;
        shinka_rates_get(&battle, &dv, &fixed);
        if ((READ(p + 0xa4) & ~1u) != rate_tag(battle, dv, fixed)) {
            refresh_menu(p, READ(p + 0xa0), row < (short_settings(READ(p + 0xa0)) ? 3u : 8u) ? row : 0);
            return; /* current settings remain authoritative after state load */
        }
    }
    if (READ(p + 0xa0) == 6) {
        if ((pressed & button(14)) || (row == 2 && (pressed & button(13)))) {
            WRITE(p + 0xa4, 0); refresh_menu(p, 1, 4);
        } else if (row < 2 && (pressed & (button(5) | button(7) | button(13)))) {
            int option = row == 0 ? 0 : 2;
            WRITE(p + 0xa4, !shinka_view_set(option, !shinka_view_get(option)));
            refresh_menu(p, 6, row);
        }
        return;
    }
    if (READ(p + 0xa0) == 4) {
        if ((pressed & button(14)) || (row == 2 && (pressed & button(13)))) {
            WRITE(p + 0xa4, 0); refresh_menu(p, 1, 6);
        } else if (row < 2 && (pressed & (button(5) | button(7) | button(13)))) {
            static const int rates[] = {100, 125, 150, 200};
            int direction = pressed & button(7) ? -1 : 1;
            int next = (motion_index(shinka_motion_get(row)) + direction + 4) % 4;
            WRITE(p + 0xa4, !shinka_motion_set(row, rates[next]));
            refresh_menu(p, 4, row);
        }
        return;
    }
    if ((pressed & button(14)) || (row == 7 && (pressed & button(13)))) {
        WRITE(p + 0xa4, 0); refresh_menu(p, 0, count - 1);
    } else if (row == 6 && (pressed & button(13))) {
        WRITE(p + 0xa4, 0); refresh_menu(p, 4, 0);
    } else if (row == 4 && (pressed & button(13))) {
        WRITE(p + 0xa4, 0); refresh_menu(p, 6, 0);
    } else if (row < 6 && (pressed & (button(5) | button(7) | button(13)))) {
        int battle, dv, fixed, direction = pressed & button(7) ? -1 : 1;
        if (row == 4) return; /* Screen view opens with confirm. */
        if (row == 5) {
            int option = 1, choices = 3;
            int next = (shinka_view_get(option) + direction + choices) % choices;
            WRITE(p + 0xa4, !shinka_view_set(option, next));
            refresh_menu(p, 1, row);
            return;
        }
        if (row == 3) {
            int next = (shinka_music_palette_get() + direction + 4) % 4;
            WRITE(p + 0xa4, !shinka_music_palette_set(next));
            refresh_menu(p, 1, row);
            return;
        }
        if (row == 2) {
            int next = (shinka_encounter_rate_get() / 50 + direction + 5) % 5 * 50;
            WRITE(p + 0xa4, !shinka_encounter_rate_set(next));
            refresh_menu(p, 1, row);
            return;
        }
        shinka_rates_get(&battle, &dv, &fixed);
        if (row == 0) battle = (battle - 1 + direction + 4) % 4 + 1;
        else {
            int index = ((fixed ? 4 : dv - 1) + direction + 5) % 5;
            dv = index == 4 ? 1 : index + 1; fixed = index == 4 ? 10 : 0;
        }
        WRITE(p + 0xa4, !shinka_rates_set(battle, dv, fixed));
        shinka_rewards_refresh();
        refresh_menu(p, 1, row);
    }
}

void shinka_journal_transition(CPUState* cpu) {
    uint32_t mode = READ(MODE), p = cpu->gpr[17];
    if ((mode >> 8) == 2 && cpu->gpr[4] == STATUS && cpu->gpr[31] == 0x80013334
        && expanded(p) && READ(p + 0x58) == 5 + (READ(p + 0x60) != 0)) {
        WRITE(p + 0x58, 4); cpu->gpr[4] = enabled ? JOURNAL : STATUS;
    } else if (mode == STATUS && cpu->gpr[31] == 0x80013318
               && cpu->gpr[4] == READ(0x80048d68) && (cpu->gpr[4] >> 8) == 2
               && expanded(p) && READ(p + 0xa0) == 3) {
        WRITE(0x8005ccf0, 4); WRITE(p + 0x58, 4);
        cpu->gpr[4] = enabled ? JOURNAL : STATUS;
    } else if (mode == JOURNAL && cpu->gpr[31] == 0x8008ee8c
               && cpu->gpr[4] == READ(0x80048d68) && (cpu->gpr[4] >> 8) == 2) {
        WRITE(0x8005ccf0, 4); cpu->gpr[4] = STATUS;
        cpu->gpr[5] = LAB_ROOT_RETURN;
    }
}
