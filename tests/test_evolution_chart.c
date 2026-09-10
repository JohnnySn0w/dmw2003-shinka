#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cpu_state.h"
#include "mod_plugins.h"
#include "evolution_data.h"

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); exit(1); } } while (0)
static unsigned char memory[8 * 1024 * 1024], scratchpad[1024];
static unsigned writes;
static int active = 1, watch;
static const uint32_t panel = 0x800f0000;
static unsigned char* ptr(uint32_t a) {
    if (a >= 0x1f800000 && a < 0x1f800400) return scratchpad + (a - 0x1f800000);
    CHECK((a & 0x1fffffff) < sizeof(memory)); return memory + (a & 0x1fffffff);
}
uint8_t psx_mod_read_byte(uint32_t a) { return *ptr(a); }
uint16_t psx_mod_read_half(uint32_t a) { uint16_t v; memcpy(&v, ptr(a), 2); return v; }
uint32_t psx_mod_read_word(uint32_t a) { uint32_t v; memcpy(&v, ptr(a), 4); return v; }
static void writing(uint32_t a) {
    if (watch) CHECK((a >= panel + 0xd0 && a < panel + 0x210) || a == panel + 0xcc || a == panel + 0xc0
        || a == panel + 0x290 || a == panel + 0x294 || (a >= 0x80400000 && a < 0x80400200));
    ++writes;
}
void psx_mod_write_word(uint32_t a, uint32_t v) { writing(a); memcpy(ptr(a), &v, 4); }
void psx_mod_write_half(uint32_t a, uint16_t v) { writing(a); memcpy(ptr(a), &v, 2); }
void psx_mod_write_byte(uint32_t a, uint8_t v) { writing(a); *ptr(a) = v; }
uint32_t psx_mod_alloc_guest_memory(uint32_t size, uint32_t alignment) { CHECK(size <= 512); return 0x80400000; }
int shinka_journal_enabled(void) { return active; }
void shinka_chart_rebuild(uint32_t);
void shinka_chart_frame(CPUState*);
void shinka_chart_text(CPUState*);
void shinka_chart_resource(CPUState*);
void shinka_chart_sprite(CPUState*);
void shinka_chart_selection_reset(void);
#define W psx_mod_write_word
#define H psx_mod_write_half
#define R psx_mod_read_word

static void fixture(unsigned rookie) {
    watch = 0; memset(memory, 0, sizeof(memory));
    W(0x8004b3f8, 0xd01); W(0x80055d28, 13); W(0x8005cca8, 2);
    W(0x800842f4, 0x27bdffc8); W(0x8008fd70, 0x8008f768);
    W(panel + 0x28, 0x80014274); W(panel + 0x48, 0x800842f4);
    W(panel + 0x20, 7); W(panel + 0xbc, rookie); W(panel + 0xc, 1); W(panel + 0x10, 3);
    for (unsigned row = 0; row < 16; ++row) for (unsigned col = 0; col < 5; ++col)
        H(0x8008f76a + rookie * 192 + row * 12 + col * 2, evolution_layout[rookie][row][col]);
}

static void decode(uint32_t p, char* out) {
    unsigned c;
    while ((c = psx_mod_read_byte(p++)) != 0) {
        if (c == 1) { c = psx_mod_read_byte(p++); c = c == 1 ? ' ' : c == 5 ? '.' : '?'; }
        else if (c == 2) { ++p; c = '\n'; }
        else c += c >= 40 ? 57 : c >= 14 ? 51 : '0' - 4;
        *out++ = (char)c;
    }
    *out = 0;
}

static void chart_place_tests(void) {
    CPUState cpu = {0};
    uint32_t choices[8];
    shinka_chart_selection_reset();
    for (unsigned rookie = 0; rookie < 8; ++rookie) {
        fixture(rookie); W(panel + 0xb8, 44);
        for (unsigned i = 0; i < 44; ++i) H(panel + 0x60 + i * 2, evolution_ids[i + 8]);
        shinka_chart_rebuild(panel);
        unsigned page = 1 + rookie % 3, cell;
        for (cell = 19; cell > 0 && !R(panel + 0xd0 + page * 80 + cell * 4); --cell) {}
        choices[rookie] = R(panel + 0xd0 + page * 80 + cell * 4);
        CHECK(choices[rookie] && choices[rookie] != 0xffffffffu);
        W(panel + 0xc0, page); W(panel + 0x290, cell % 5); W(panel + 0x294, cell / 5);
        cpu.gpr[29] = 0x1f8002d4; W(cpu.gpr[29] + 0xe0, panel);
        cpu.gpr[31] = 0x800836d4; watch = 1; shinka_chart_frame(&cpu);
    }
    for (unsigned rookie = 0; rookie < 8; ++rookie) {
        fixture(rookie); W(panel + 0xb8, 44);
        for (unsigned i = 0; i < 44; ++i) H(panel + 0x60 + i * 2, evolution_ids[i + 8]);
        /* A fresh chart's first draw must not replace the remembered place. */
        W(panel + 0xc, 0); cpu.gpr[31] = 0x800836d4;
        W(cpu.gpr[29] + 0xe0, panel); watch = 1; shinka_chart_frame(&cpu);
        cpu.gpr[20] = panel; cpu.gpr[31] = 0x800846cc; shinka_chart_text(&cpu);
        unsigned page = R(panel + 0xc0), row = R(panel + 0x294), col = R(panel + 0x290);
        CHECK(page == 1 + rookie % 3);
        CHECK(R(panel + 0xd0 + page * 80 + row * 20 + col * 4) == choices[rookie]);
        CHECK(R(panel + 0xcc) > row);
    }
    /* Row compaction may move the form; restore identity rather than a cell. */
    fixture(7); W(panel + 0xb8, 1); H(panel + 0x60, (uint16_t)choices[7]);
    cpu.gpr[31] = 0x800846cc; watch = 1; shinka_chart_text(&cpu);
    CHECK(R(panel + 0xc0) == 2);
    CHECK(R(panel + 0xd0 + 160 + R(panel + 0x294) * 20 + R(panel + 0x290) * 4) == choices[7]);
    /* Unknown forms cannot be revealed by an old place; physical labs and
     * unsupported layouts cannot receive a portable chart bookmark. */
    for (unsigned rejection = 0; rejection < 4; ++rejection) {
        fixture(7);
        if (rejection != 0) {
            W(panel + 0xb8, 44);
            for (unsigned i = 0; i < 44; ++i) H(panel + 0x60 + i * 2, evolution_ids[i + 8]);
        }
        if (rejection == 1) W(0x8004b3f8, 0xd00);
        if (rejection == 2) H(0x8008f76a + 7 * 192, 0xdead);
        if (rejection == 3) shinka_chart_selection_reset();
        shinka_chart_rebuild(panel); cpu.gpr[31] = 0x800846cc;
        watch = 1; shinka_chart_text(&cpu); CHECK(R(panel + 0xc0) == 0);
    }
    shinka_chart_selection_reset();
}

int main(void) {
    chart_place_tests();
    CPUState cpu = {0};
    char text[512];
    for (unsigned rookie = 0; rookie < 8; ++rookie) {
        fixture(rookie); watch = 1; shinka_chart_rebuild(panel);
        for (unsigned i = 0; i < 80; ++i) {
            uint32_t id = R(panel + 0xd0 + i * 4);
            if (id != 0 && id != 0xffffffff) {
                int found = 0;
                for (unsigned j = 0; j < 52; ++j) found |= evolution_ids[j] == id;
                CHECK(found);
            }
        }
        CHECK(R(panel + 0xcc) <= 4);
        active = 0; shinka_chart_rebuild(panel);
        for (unsigned page = 0; page < 4; ++page) CHECK(R(panel + 0xd0 + page * 80) == 0xffffffff);
        active = 1;
    }
    fixture(7); W(panel + 0xb8, 1); H(panel + 0x60, 20); /* Angemon */
    cpu.gpr[29] = 0x1f8002d4; W(cpu.gpr[29] + 0xe0, panel); cpu.gpr[31] = 0x800836d4;
    watch = 1; shinka_chart_frame(&cpu);
    CHECK(R(panel + 0xd0) == 20 && R(panel + 0xd4) == 211 && R(panel + 0xd8) == 0);
    writes = 0; shinka_chart_rebuild(panel); CHECK(writes == 0); /* stable frames */
    watch = 0; W(panel + 0x290, 1); cpu.gpr[22] = 0; cpu.gpr[19] = 1;
    cpu.gpr[31] = 0x80084128; cpu.gpr[4] = 0x2c50001;
    shinka_chart_resource(&cpu); CHECK(cpu.gpr[4] == 0x2c50000);
    cpu.gpr[31] = 0x80084144; cpu.gpr[5] = 19;
    shinka_chart_sprite(&cpu); CHECK(cpu.gpr[5] == 0x3f);
    cpu.gpr[19] = 0; cpu.gpr[5] = 19; shinka_chart_sprite(&cpu); CHECK(cpu.gpr[5] == 19);

    /* A synthetic name table provides only an already known prerequisite. */
    const uint32_t names = 0x800c0000, string = 0x800c1000;
    H(0x80044b3c, 3); W(0x80044b40, 0x50); W(0x80044b48, names);
    W(names, 256); W(names + 4 + evolution_name_ids[15] * 4, string - names);
    for (unsigned i = 0; "Angemon"[i]; ++i) {
        unsigned c = (unsigned char)"Angemon"[i];
        psx_mod_write_byte(string + i, (uint8_t)(c >= 'a' ? c - 57 : c - 51));
    }
    cpu.gpr[20] = panel; cpu.gpr[31] = 0x800846cc; cpu.gpr[5] = names;
    shinka_chart_selection_reset(); /* These text tests start without a bookmark. */
    watch = 1; shinka_chart_text(&cpu);
    /* Preserve the stock title's text substitution opcode and slot. */
    CHECK(psx_mod_read_byte(cpu.gpr[5]) == 2 && psx_mod_read_byte(cpu.gpr[5] + 1) == 5
        && psx_mod_read_byte(cpu.gpr[5] + 2) == 1 && cpu.gpr[6] == 0xffffffffu);
    cpu.gpr[31] = 0x800850bc; cpu.gpr[5] = names;
    watch = 1; shinka_chart_text(&cpu); decode(cpu.gpr[5], text);
    CHECK(strcmp(text, "Unknown digivolution") == 0);
    cpu.gpr[31] = 0x800850e8; shinka_chart_text(&cpu); decode(cpu.gpr[5], text);
    CHECK(strcmp(text, "Grow stronger alongside your partner.") == 0);
    for (unsigned i = 0; text[i]; ++i) CHECK(text[i] < '0' || text[i] > '9');
    active = 0; shinka_chart_rebuild(panel);
    CHECK(R(panel + 0xd0) == 20 && R(panel + 0xd4) == 0 && R(panel + 0x290) == 0);
    active = 1; watch = 0;
    H(panel + 0x60, 367); /* Growlmon leads to another anonymous branch. */
    shinka_chart_rebuild(panel);
    unsigned cell;
    for (cell = 0; cell < 80 && R(panel + 0xd0 + cell * 4) != 386; ++cell) {}
    CHECK(cell < 80);
    W(panel + 0xc0, cell / 20); W(panel + 0x294, cell % 20 / 5); W(panel + 0x290, cell % 5);
    W(names + 4 + evolution_name_ids[13] * 4, string - names);
    for (unsigned i = 0; "Growlmon"[i]; ++i) {
        unsigned c = (unsigned char)"Growlmon"[i];
        psx_mod_write_byte(string + i, (uint8_t)(c >= 'a' ? c - 57 : c - 51));
    }
    psx_mod_write_byte(string + 8, 0);
    cpu.gpr[31] = 0x800850bc; cpu.gpr[5] = names; shinka_chart_text(&cpu);
    cpu.gpr[31] = 0x800850e8; shinka_chart_text(&cpu); decode(cpu.gpr[5], text);
    CHECK(strstr(text, "Growlmon") != NULL && strstr(text, "Grizzmon") == NULL);
    W(panel + 0xb8, 0); cpu.gpr[5] = 0;
    shinka_chart_text(&cpu); decode(cpu.gpr[5], text);
    CHECK(strcmp(text, "Explore other evolution paths.") == 0);
    H(0x8008f76a + 7 * 192, 0xdead);
    writes = 0; shinka_chart_rebuild(panel); CHECK(writes == 0);
    W(0x8004b3f8, 0x249); writes = 0; shinka_chart_rebuild(panel); CHECK(writes == 0);
    puts("Chart discovery, hidden artwork/names, scratchpad stack, revision and ownership guards passed.");
    return 0;
}
