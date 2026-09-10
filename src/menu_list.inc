/* The six original row slots remain in place. Two additional text tasks live
 * after all original children, so cursor/party offsets and old states survive. */
#include <stdio.h>
extern void shinka_rates_get(int*, int*, int*);
extern int shinka_rates_set(int, int, int);
extern int shinka_encounter_rate_get(void);
extern int shinka_encounter_rate_set(int);
extern int shinka_music_palette_get(void);
extern int shinka_music_palette_set(int);
extern void shinka_rewards_refresh(void);
extern void shinka_rewards_tick(void);
extern void shinka_rewards_activate(void);
static uint32_t text_scratch;
static uint32_t panel_scratch;

static int expanded(uint32_t p) {
    return object(p, QUICK_MENU) && READ(p + 0x20) == 0x2d;
}

static uint32_t rate_tag(int battle, int dv, int fixed) {
    return (uint32_t)((battle << 8) | (dv << 12) | (fixed ? 0x10000 : 0)
        | ((shinka_encounter_rate_get() / 50 + 1) << 20)
        | (shinka_music_palette_get() << 24));
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
        label = READ(p + 0xa4) & 1 ? "Settings save failed" : READ(p + 0xa0) == 1
            ? (shinka_music_palette_get() ? "Alt audio playback pending" : "SETTINGS: Left Right") : READ(MODE) == STATUS
            ? "Triangle: Close Status" : "Triangle: Close Menu";
    } else if (cpu->gpr[31] == 0x80012938) {
        row = READ(p + 0x18);
        if (row >= 8) return;
        if (READ(p + 0xa0) == 1) {
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
            } else label = row == 4 ? "BACK" : "";
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
    rows = READ(p + 0xa0) == 1 ? 5 : (enabled ? 7 : 5) + (READ(p + 0x60) != 0);
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
    WRITE(p + 0x5c, 7 + (READ(p + 0x60) != 0));
    if (object(cursor, 0x8001b0a4)) {
        WRITE(cursor + 0x58, 176); WRITE(cursor + 0x5c, 49 + 14 * selection);
        WRITE(cursor + 0x68, 1); /* request the stock cursor's position update */
    }
    psx_mod_write_half(0x8004b818, 0);
}

void shinka_journal_quick_menu(CPUState* cpu) {
    uint32_t p = cpu->gpr[4], row, count;
    uint16_t pressed;
    if (!expanded(p) || READ(0x8004b3fc)) return;
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
    count = 7 + (READ(p + 0x60) != 0);
    if (!enabled) {
        /* A save made with this layout still owns the appended children.
         * Keep safe addressing/teardown, but do not expose disabled actions. */
        if (READ(p + 0xa0) != 2 && READ(p + 0x10) == 3)
            refresh_menu(p, 2, READ(p + 0x58) < count - 2 ? READ(p + 0x58) : 4);
        WRITE(p + 0x5c, READ(p + 0x10) == 3 ? count - 2 : count);
        return;
    }
    if (READ(p + 0xa0) == 1 && READ(p + 0x10) == 3 && READ(p + 0x5c) == 4) {
        /* Rebuild an old four-row savestate before BACK becomes Soundtrack. */
        refresh_menu(p, 1, READ(p + 0x58) == 3 ? 4 : READ(p + 0x58));
        return;
    }
    WRITE(p + 0x5c, READ(p + 0xa0) == 1 && READ(p + 0x10) == 3 ? 5 : count);
    if (READ(p + 0x10) != 3) return;
    if (READ(p + 0xa0) > 1) { refresh_menu(p, 0, 4); return; }
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
            refresh_menu(p, 1, row < 5 ? row : 0);
            return; /* current settings remain authoritative after state load */
        }
    }
    if ((pressed & button(14)) || (row == 4 && (pressed & button(13)))) {
        WRITE(p + 0xa4, 0); refresh_menu(p, 0, count - 1);
    } else if (row < 4 && (pressed & (button(5) | button(7) | button(13)))) {
        int battle, dv, fixed, direction = pressed & button(7) ? -1 : 1;
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
