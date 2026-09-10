#include <stdio.h>
#include <string.h>
#include "cpu_state.h"
#include "mod_plugins.h"
#include "evolution_data.h"

extern int shinka_journal_enabled(void);
#define R psx_mod_read_word
#define H psx_mod_read_half
#define B psx_mod_read_byte
#define W psx_mod_write_word

static int ram(uint32_t p, uint32_t size) {
    return p >= 0x80010000u && p <= 0x80200000u - size;
}

static int draw_stack(uint32_t p) {
    return ram(p, 0xe4) || (p >= 0x1f800000u && p <= 0x1f800400u - 0xe4);
}

static int profile(uint32_t id) {
    unsigned i;
    for (i = 0; i < 52; ++i) if (evolution_ids[i] == id) return (int)i;
    return -1;
}

static int chart(uint32_t p) {
    uint32_t mode = R(0x8004b3f8);
    return (mode == 0xd00 || mode == 0xd01) && R(0x80055d28) == 13
        && R(0x800842f4) == 0x27bdffc8 && R(0x8008fd70) == 0x8008f768
        && ram(p, 0x29c) && !(p & 3) && R(p + 0x28) == 0x80014274
        && R(p + 0x48) == 0x800842f4 && R(p + 0x20) == 7
        && R(p + 0xb8) <= 44 && R(p + 0xbc) < 8 && R(p + 0xc0) < 4;
}

static int known(uint32_t p, uint32_t id) {
    unsigned i, count = R(p + 0xb8);
    if (id == evolution_ids[R(p + 0xbc)]) return 1;
    for (i = 0; i < count; ++i) if (H(p + 0x60 + i * 2) == id) return 1;
    return 0;
}

static int available(void) {
    return shinka_journal_enabled() && R(0x8005cca8) == 2;
}

static struct { uint32_t id, page; } chart_places[8];

void shinka_chart_selection_reset(void) {
    memset(chart_places, 0, sizeof(chart_places));
}

static int layout_matches(uint32_t p) {
    unsigned rookie = R(p + 0xbc), row, col;
    for (row = 0; row < 16; ++row) for (col = 0; col < 5; ++col)
        if (H(0x8008f76a + rookie * 192 + row * 12 + col * 2)
            != evolution_layout[rookie][row][col]) return 0;
    return 1;
}

static uint32_t selected(uint32_t p) {
    unsigned page = R(p + 0xc0), row = R(p + 0x294), col = R(p + 0x290);
    return row < 4 && col < 5 ? R(p + 0xd0 + page * 80 + row * 20 + col * 4) : 0;
}

static int nearby(uint32_t p, uint32_t id) {
    int index = profile(id);
    const uint8_t* req;
    if (index < 8) return 0;
    req = evolution_requirements[R(p + 0xbc)][index - 8];
    return req[2] == 7 || (req[0] && known(p, evolution_ids[req[0] - 1]))
        || (req[1] && known(p, evolution_ids[req[1] - 1]));
}

/* Rebuild only the chart's display cache. The partner's ownership, equipped
 * forms and reward/unlock records are never changed. Hidden nodes retain their
 * IDs internally so the stock cursor and detail panel can still operate. */
void shinka_chart_rebuild(uint32_t p) {
    uint32_t matrix[80] = {0}, counts[4] = {0}, old_selection;
    unsigned page, row, col, rookie, changed = 0;
    int hints = available();
    if (!chart(p) || !layout_matches(p)) return;
    rookie = R(p + 0xbc);
    old_selection = selected(p);
    for (page = 0; page < 4; ++page) {
        for (row = 0; row < 4; ++row) {
            const uint16_t* forms = evolution_layout[rookie][page * 4 + row];
            uint32_t visible[5] = {0};
            int last_known = -1, frontier = -1;
            unsigned any = 0;
            for (col = 0; col < 5; ++col)
                if (forms[col] && known(p, forms[col])) last_known = (int)col;
            if (hints) for (col = (unsigned)(last_known + 1); col < 5; ++col) {
                if (!forms[col]) continue;
                if (last_known >= 0 || nearby(p, forms[col])) frontier = (int)col;
                break; /* one unknown step, not every later form */
            }
            for (col = 0; col < 5; ++col) {
                if (forms[col] && (known(p, forms[col])
                    || (hints && ((int)col <= last_known || (int)col == frontier)))) {
                    visible[col] = forms[col]; any = 1;
                }
            }
            if (any) {
                memcpy(matrix + page * 20 + counts[page] * 5, visible, sizeof(visible));
                ++counts[page];
            }
        }
        if (!counts[page]) matrix[page * 20] = 0xffffffffu;
    }
    for (col = 0; col < 80; ++col) if (R(p + 0xd0 + col * 4) != matrix[col]) {
        W(p + 0xd0 + col * 4, matrix[col]); changed = 1;
    }
    page = R(p + 0xc0);
    if (R(p + 0xcc) != counts[page]) W(p + 0xcc, counts[page]);
    if (changed || !selected(p)) {
        unsigned choice = 0;
        for (col = 0; col < 20; ++col) if (matrix[page * 20 + col] == old_selection && old_selection) {
            choice = col; break;
        }
        if (col == 20) for (col = 0; col < 20; ++col)
            if (matrix[page * 20 + col]) { choice = col; break; }
        W(p + 0x290, choice % 5); W(p + 0x294, choice / 5);
    }
}

void shinka_chart_frame(CPUState* cpu) {
    uint32_t p, id, rookie;
    if (cpu->gpr[31] != 0x800836d4 || !draw_stack(cpu->gpr[29])) return;
    p = R(cpu->gpr[29] + 0xe0);
    shinka_chart_rebuild(p);
    /* Observe the native chart's normal input phase, never its initial draw,
     * page animation or teardown. Bookmarks contain form identity, not slots. */
    if (!available() || R(0x8004b3f8) != 0xd01 || !chart(p)
        || !layout_matches(p) || R(p + 0xc) != 1 || R(p + 0x10) != 3) return;
    id = selected(p); rookie = R(p + 0xbc);
    if (profile(id) < 0) return;
    chart_places[rookie].id = id;
    chart_places[rookie].page = R(p + 0xc0);
}

static void restore_chart_place(uint32_t p) {
    uint32_t rookie, page, id;
    unsigned cell, rows = 0;
    if (R(0x8004b3f8) != 0xd01 || !layout_matches(p)) return;
    rookie = R(p + 0xbc); page = chart_places[rookie].page;
    id = chart_places[rookie].id;
    if (!id || page >= 4) return;
    shinka_chart_rebuild(p);
    for (cell = 0; cell < 20; ++cell)
        if (R(p + 0xd0 + page * 80 + cell * 4) == id) break;
    if (cell == 20) return; /* A bookmark must not reveal a now-hidden form. */
    for (unsigned row = 0; row < 4; ++row)
        for (unsigned col = 0; col < 5; ++col) {
            uint32_t form = R(p + 0xd0 + page * 80 + row * 20 + col * 4);
            if (form && form != 0xffffffffu) { ++rows; break; }
        }
    W(p + 0xc0, page); W(p + 0xcc, rows);
    W(p + 0x290, cell % 5); W(p + 0x294, cell / 5);
}

static int hidden_icon(CPUState* cpu, int resource) {
    uint32_t p, id, ra = cpu->gpr[31];
    if (!available() || !draw_stack(cpu->gpr[29])) return 0;
    if (ra != (resource ? 0x80084128u : 0x80084144u)
        && ra != (resource ? 0x800837d0u : 0x800837ecu)
        && ra != (resource ? 0x80083870u : 0x8008388cu)) return 0;
    p = R(cpu->gpr[29] + 0xe0);
    if (!chart(p)) return 0;
    if (ra == (resource ? 0x80084128u : 0x80084144u)) {
        unsigned row = cpu->gpr[22], col = cpu->gpr[19];
        if (row >= 4 || col >= 5) return 0;
        id = R(p + 0xd0 + R(p + 0xc0) * 80 + row * 20 + col * 4);
    } else id = selected(p);
    return profile(id) >= 8 && !known(p, id);
}

void shinka_chart_resource(CPUState* cpu) {
    if (cpu->gpr[4] == 0x02c50001 && hidden_icon(cpu, 1)) cpu->gpr[4] = 0x02c50000;
}

void shinka_chart_sprite(CPUState* cpu) {
    uint32_t ra = cpu->gpr[31], p, x;
    int hidden;
    if (!available() || !draw_stack(cpu->gpr[29])
        || (ra != 0x80084144 && ra != 0x800837ec && ra != 0x8008388c)) return;
    p = R(cpu->gpr[29] + 0xe0);
    if (!chart(p)) return;
    hidden = hidden_icon(cpu, 0);
    if (hidden) cpu->gpr[5] = 0x3f; /* original anonymous node */
    /* The portrait and frame sheets occupy different VRAM pages. This local
     * draw context is reconstructed by the original renderer each frame. */
    x = hidden ? 640 : 320;
    W(cpu->gpr[29] + 0x18, x); W(cpu->gpr[29] + 0x20, x);
}

static uint32_t scratch;

static uint32_t name_table(void) {
    /* Resident resource directory, as searched by 0x800139fc. Resolve anew
     * after savestate loads; no host cache determines what the player knows. */
    unsigned i;
    for (i = 0; i < 64; ++i) {
        uint32_t entry = 0x80044b3c + i * 16;
        if (H(entry) == 3 && R(entry + 4) == 0x50) return R(entry + 12);
    }
    return 0;
}

static int read_name(uint32_t table, unsigned index, char* out, size_t size) {
    uint32_t string;
    unsigned n = 0;
    if (!ram(table, 4) || R(table) > 2048 || index >= R(table)
        || !ram(table, 8 + index * 4)) return 0;
    string = table + R(table + 4 + index * 4);
    if (!ram(string, 80)) return 0;
    while (n + 1 < size) {
        unsigned c = B(string++);
        if (!c) { out[n] = 0; return n != 0; }
        if (c >= 14 && c <= 39) c += 51;
        else if (c >= 40 && c <= 65) c += 57;
        else if (c >= 4 && c <= 13) c += '0' - 4;
        else if (c == 1) {
            c = B(string++);
            c = c == 1 ? ' ' : c == 13 ? '-' : 0;
            if (!c) return 0;
        } else return 0;
        out[n++] = (char)c;
    }
    return 0;
}

static uint32_t encode_hint(const char* text) {
    unsigned n = 4;
    if (!scratch || R(scratch) != 0x48494e54) {
        scratch = psx_mod_alloc_guest_memory(512, 4);
        if (!scratch) return 0;
        W(scratch, 0x48494e54);
    }
    while (*text && n < 508) {
        unsigned c = (unsigned char)*text++;
        if (c == 2 && (unsigned char)text[0] == 5 && (unsigned char)text[1] == 1) {
            /* The stock title substitutes the selected partner's name here. */
            psx_mod_write_byte(scratch + n++, 2); psx_mod_write_byte(scratch + n++, 5);
            psx_mod_write_byte(scratch + n++, 1); text += 2;
        } else if (c == ' ' || c == '.' || c == '-' || c == '?' || c == ':') {
            psx_mod_write_byte(scratch + n++, 1);
            psx_mod_write_byte(scratch + n++, c == ' ' ? 1 : c == '.' ? 5 : c == '-' ? 13 : c == ':' ? 7 : 9);
        } else if (c == '\n') {
            psx_mod_write_byte(scratch + n++, 2); psx_mod_write_byte(scratch + n++, 1);
        } else psx_mod_write_byte(scratch + n++, (uint8_t)(c >= 'a' && c <= 'z' ? c - 57
            : c >= 'A' && c <= 'Z' ? c - 51 : c >= '0' && c <= '9' ? c - '0' + 4 : 0));
    }
    psx_mod_write_byte(scratch + n, 0);
    return scratch + 4;
}

static const char* directions[] = {
    "", "Develop greater strength.", "Build your physical defenses.",
    "Strengthen your spirit.", "Cultivate your wisdom.", "Develop your speed.",
    "Develop your charisma.", "Grow stronger alongside your partner.",
    "Train your affinity with fire.", "Train your affinity with water.",
    "Train your affinity with ice.", "Train your affinity with wind.",
    "Train your affinity with thunder.", "Train your affinity with machines.",
    "Train your affinity with darkness."
};

void shinka_chart_text(CPUState* cpu) {
    uint32_t p = cpu->gpr[20], ra = cpu->gpr[31], text;
    int index;
    char hint[256] = "";
    unsigned i, hidden = 0;
    const uint8_t* req;
    if (!available() || (ra != 0x800846cc && ra != 0x800850bc && ra != 0x800850e8) || !chart(p)) return;
    if (ra == 0x800846cc) {
        /* Initial title setup precedes the native page-number widget. */
        restore_chart_place(p);
        text = encode_hint("\x02\x05\x01 - X: Hints");
        if (text) { cpu->gpr[5] = text; cpu->gpr[6] = 0xffffffffu; }
        return;
    }
    index = profile(selected(p));
    if (index < 8 || known(p, evolution_ids[index])) return;
    if (ra == 0x800850bc) {
        text = encode_hint("Unknown digivolution");
    } else {
        uint32_t names = name_table();
        req = evolution_requirements[R(p + 0xbc)][index - 8];
        for (i = 0; i < 2; ++i) if (req[i] && (i == 0 || req[i] != req[0])) {
            char name[40];
            if (known(p, evolution_ids[req[i] - 1])
                && read_name(names, evolution_name_ids[req[i] - 1], name, sizeof(name))) {
                size_t n = strlen(hint);
                snprintf(hint + n, sizeof(hint) - n, "%sDeepen your mastery of %s.", n ? "\n" : "", name);
            } else hidden = 1;
        }
        if (hidden) strcat(hint, *hint ? "\nExplore other evolution paths." : "Explore other evolution paths.");
        if (req[2]) { if (*hint) strcat(hint, "\n"); strcat(hint, directions[req[2]]); }
        text = encode_hint(hint);
    }
    if (text) { cpu->gpr[5] = text; cpu->gpr[6] = 0xffffffffu; }
}
