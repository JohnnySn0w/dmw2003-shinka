#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cpu_state.h"
#include "mod_plugins.h"
#include "../src/menu_wide.h"

static unsigned char ram[8388608];
static unsigned writes;
static PSXModActivationCallback activate;
static PSXModVBlankCallback tick;
#define CHECK(c) do { if (!(c)) { fprintf(stderr, "line %d: %s\n", __LINE__, #c); exit(1); } } while (0)
static unsigned offset(uint32_t a) { CHECK((a & 0x1fffffffu) < sizeof(ram)); return a & 0x1fffffffu; }
int psx_mod_register_activation_plugin(const char *id, PSXModActivationCallback cb) { activate = cb; return 1; }
int psx_mod_register_vblank_plugin(const char *id, PSXModVBlankCallback cb) { tick = cb; return 1; }
int psx_mod_game_started(void) { return 1; }
uint8_t psx_mod_read_byte(uint32_t a) { return ram[offset(a)]; }
uint16_t psx_mod_read_half(uint32_t a) { uint16_t v; memcpy(&v, ram + offset(a), 2); return v; }
uint32_t psx_mod_read_word(uint32_t a) { uint32_t v; memcpy(&v, ram + offset(a), 4); return v; }
void psx_mod_write_word(uint32_t a, uint32_t v) { memcpy(ram + offset(a), &v, 4); ++writes; }
void psx_mod_write_half(uint32_t a, uint16_t v) { memcpy(ram + offset(a), &v, 2); ++writes; }
void psx_mod_write_byte(uint32_t a, uint8_t v) { ram[offset(a)] = v; ++writes; }
void psx_mod_write_code_word(uint32_t a, uint32_t v) { psx_mod_write_word(a, v); }
void shinka_journal_quick_menu(CPUState *cpu);
void shinka_menu_text(CPUState *cpu);
void shinka_journal_transition(CPUState *cpu);
void shinka_menu_allocate(CPUState *cpu);
void shinka_menu_task_ready(CPUState *cpu);
void shinka_register_journal(void);
void shinka_lab_selection_reset(void);
int shinka_menu_root_active(void);
int shinka_menu_items_active(void);
void shinka_chart_selection_reset(void) {}
#define W psx_mod_write_word
#define R psx_mod_read_word

static int battle_rate = 3, dv_rate = 1, fixed_rate = 10, fail_save;
static int encounter_rate = 100;
static int music_palette;
static int view_options[3];
static int motion_options[2] = {100, 100};
int shinka_motion_get(int option) { return motion_options[option]; }
int shinka_motion_set(int option, int value) { if (fail_save) return 0; motion_options[option]=value; return 1; }
int shinka_view_get(int option) { return view_options[option]; }
int shinka_view_set(int option, int value) { if (fail_save) return 0; view_options[option]=value; return 1; }
int shinka_music_palette_get(void) { return music_palette; }
int shinka_music_available(void) { return 1; }
int shinka_music_palette_set(int palette) { if (fail_save) return 0; music_palette = palette; return 1; }
int shinka_encounter_rate_get(void) { return encounter_rate; }
int shinka_encounter_rate_set(int rate) { if (fail_save) return 0; encounter_rate = rate; return 1; }
uint32_t psx_mod_alloc_guest_memory(uint32_t size, uint32_t alignment) { return 0x80400000; }
void shinka_rates_get(int* battle, int* dv, int* fixed) { *battle=battle_rate; *dv=dv_rate; *fixed=fixed_rate; }
int shinka_rates_set(int battle, int dv, int fixed) { if (fail_save) return 0; battle_rate=battle; dv_rate=dv; fixed_rate=fixed; return 1; }
void shinka_rewards_refresh(void) {}
void shinka_rewards_tick(void) {}
void shinka_rewards_activate(void) {}
uint32_t shinka_menu_slot(uint32_t, uint32_t);

int main(void) {
    CPUState cpu = {0};
    shinka_register_journal();
    const uint32_t menu = 0x800f0000u;
    W(0x8005cca8u, 2); W(0x8004b3f8u, 0x21d);
    W(menu + 0x28, 0x80014274u); W(menu + 0x48, 0x8001270cu);
    W(menu + 0xc, 1); W(menu + 0x10, 3); W(menu + 0x58, 4);
    ram[0x4b883] = 15; ram[0x4b881] = 13;
    psx_mod_write_half(0x8004b818u, 0x8000);
    cpu.gpr[4] = menu;
    writes = 0;
    shinka_journal_quick_menu(&cpu);
    CHECK(writes == 0); /* unselected package is inert */
    CHECK(activate && tick); activate();
    /* Both roots share the resident widget; unrelated scenes and non-English
     * menus must retain their original allocations. */
    {
        const uint32_t modes[] = {0x21d, 0x1000, 0xd00, 0x700};
        unsigned i;
        for (i = 0; i < 4; ++i) {
            W(0x8004b3f8, modes[i]);
            cpu.gpr[4] = 0x8001270c; cpu.gpr[5] = 0xa0; cpu.gpr[6] = 0xac;
            shinka_menu_allocate(&cpu);
            CHECK(cpu.gpr[5] == (i < 2 ? 0xa8 : 0xa0));
            CHECK(cpu.gpr[6] == (i < 2 ? 0xb4 : 0xac));
        }
        W(0x8004b3f8, 0x1000); W(0x8005cca8, 3);
        cpu.gpr[5] = 0xa0; cpu.gpr[6] = 0xac;
        shinka_menu_allocate(&cpu); CHECK(cpu.gpr[5] == 0xa0);
        W(0x8005cca8, 2); W(0x8004b3f8, 0x21d); cpu.gpr[4] = menu;
    }
    W(0x8004b3fcu, 0x700);
    writes = 0; shinka_journal_quick_menu(&cpu); CHECK(writes == 0);
    W(0x8004b3fcu, 0); W(menu + 0x20, 0x2d); W(menu + 0x60, 1);
    W(menu + 0x24, 0x80100000);
    CHECK(shinka_menu_slot(menu, 0x80100020) == 0x80100020);
    CHECK(shinka_menu_slot(menu, 0x80100024) == 0x801000ac);
    CHECK(shinka_menu_slot(menu, 0x80100028) == 0x801000b0);
    W(menu + 0x58, 4); shinka_journal_quick_menu(&cpu);
    CHECK(R(menu + 0x58) == 4); /* Square no longer changes STATUS */
    CHECK(shinka_menu_root_active());
    {
        /* Preserve the original encoded button hint and its colored glyph;
         * settings still supplies its custom header, then restores stock. */
        cpu.gpr[17]=menu;cpu.gpr[31]=0x8001288c;
        for(int full=0;full<2;++full) {
            W(0x8004b3f8,full ? 0x1000 : 0x21d);
            W(menu+0xa0,0);W(menu+0xa4,0);cpu.gpr[5]=0x80150000;cpu.gpr[6]=123;
            shinka_menu_text(&cpu);CHECK(cpu.gpr[5]==0x80150000 && cpu.gpr[6]==123);
            W(menu+0xa0,1);shinka_menu_text(&cpu);CHECK(cpu.gpr[5]!=0x80150000);
            W(menu+0xa0,0);cpu.gpr[5]=0x80150000;cpu.gpr[6]=123;
            shinka_menu_text(&cpu);CHECK(cpu.gpr[5]==0x80150000 && cpu.gpr[6]==123);
        }
        W(0x8004b3f8,0x21d);
    }
    {
        /* A restored root bypasses the setter. These are the actual encoded
         * legacy strings; repair both roots without moving the selected row. */
        const uint32_t header=0x80110000, text=0x80120000;
        const unsigned char old_status[] = {
            0x21,0x39,0x30,0x28,0x35,0x2e,0x33,0x2c,1,7,1,1,
            0x10,0x33,0x36,0x3a,0x2c,1,1,0x20,0x3b,0x28,0x3b,0x3c,0x3a,0};
        const unsigned char old_menu[] = {
            0x21,0x39,0x30,0x28,0x35,0x2e,0x33,0x2c,1,7,1,1,
            0x10,0x33,0x36,0x3a,0x2c,1,1,0x1a,0x2c,0x35,0x3c,0};
        W(0x80100000,header);W(header+0x28,0x80014274);W(header+0x48,0x8001ac14);
        W(header+0x114,0x800194e8);W(header+0x5c,text);
        for(int full=0;full<2;++full) {
            unsigned length=full ? sizeof(old_status) : sizeof(old_menu);
            memcpy(ram+offset(text),full ? old_status : old_menu,length);
            psx_mod_write_half(header+0x62,(uint16_t)(length-1));
            W(0x8004b3f8,full ? 0x1000 : 0x21d);W(menu+0x58,2);W(menu+0x10,3);
            shinka_journal_quick_menu(&cpu);
            CHECK(R(menu+0x10)==0 && R(menu+0x58)==2 && R(menu+0xa0)==0);
            /* Do not interrupt an accepted action or refresh unrelated text. */
            W(menu+0x10,4);shinka_journal_quick_menu(&cpu);CHECK(R(menu+0x10)==4);
            W(menu+0x10,3);ram[offset(text)+length-2]^=1;
            shinka_journal_quick_menu(&cpu);CHECK(R(menu+0x10)==3);
            ram[offset(text)+length-2]^=1;
            W(header+0x5c,0x801ffff8);shinka_journal_quick_menu(&cpu);CHECK(R(menu+0x10)==3);
            W(header+0x5c,text);W(header+0x48,0x8001b0a4);
            shinka_journal_quick_menu(&cpu);CHECK(R(menu+0x10)==3);
            W(header+0x48,0x8001ac14);
        }
        W(0x80100000,0);W(menu+0x58,4);W(0x8004b3f8,0x21d);
        shinka_journal_quick_menu(&cpu);
    }
    W(0x8004b3fc, 0x1000); CHECK(shinka_menu_root_active()); W(0x8004b3fc, 0);
    for(unsigned life=1;life<=2;++life) for(unsigned phase=0;phase<=7;++phase) {
        W(menu + 0xc,life);W(menu + 0x10,phase);CHECK(shinka_menu_root_active());
    }
    W(menu + 0xc,3);CHECK(!shinka_menu_root_active());W(menu + 0xc,1);
    W(menu + 0x10,8);CHECK(!shinka_menu_root_active());W(menu + 0x10,3);
    W(menu + 0xa0, 5); CHECK(!shinka_menu_root_active()); W(menu + 0xa0, 0);
    W(0x8004b3f8, 0x1000); CHECK(!shinka_menu_root_active());
    shinka_journal_quick_menu(&cpu); CHECK(shinka_menu_root_active());
    W(menu+0xc,3);W(menu+0x14,0);CHECK(shinka_menu_root_active()); /* final field handoff */
    W(menu+0x14,1);CHECK(!shinka_menu_root_active()); /* confirmed child takes over */
    W(menu+0xc,1);W(menu+0x14,0);
    shinka_lab_selection_reset(); CHECK(!shinka_menu_root_active());
    W(0x8004b3f8, 0x21d); shinka_journal_quick_menu(&cpu);
    CHECK(shinka_menu_root_active());
    W(menu + 0x58, 7); psx_mod_write_half(0x8004b818, 0xa000);
    shinka_journal_quick_menu(&cpu);
    CHECK(R(menu + 0xa0) == 1 && R(menu + 0x58) == 0 && R(menu + 0x10) == 0);
    W(menu + 0xa4, 0x311300); W(menu + 0x10, 3); ram[0x4b879] = 5;
    psx_mod_write_half(0x8004b818, 0x20); shinka_journal_quick_menu(&cpu);
    CHECK(battle_rate == 4); CHECK(R(menu + 0x10) == 0);
    W(menu + 0xa4, 0x311400); W(menu + 0x10, 3); W(menu + 0x58, 1); psx_mod_write_half(0x8004b818, 0x20);
    shinka_journal_quick_menu(&cpu); CHECK(dv_rate == 1 && fixed_rate == 0);
    /* Combined confirm inputs must never send the SETTINGS index to Status.
     * A persistence failure keeps the old rates and makes the error visible. */
    W(menu + 0xa4, 0x301400); W(menu + 0x10, 3); fail_save = 1;
    psx_mod_write_half(0x8004b818, 0xa020); shinka_journal_quick_menu(&cpu);
    CHECK(dv_rate == 1 && (R(menu + 0xa4) & 1) && R(menu + 0x10) == 0);
    fail_save = 0;
    W(menu + 0xa4, 0x301400); W(menu + 0x10, 3); W(menu + 0x58, 2);
    psx_mod_write_half(0x8004b818, 0x20); shinka_journal_quick_menu(&cpu);
    CHECK(encounter_rate == 150 && battle_rate == 4 && dv_rate == 1 && R(menu + 0xa0) == 1);
    W(menu + 0xa4, 0x401400); W(menu + 0x10, 3); fail_save = 1;
    psx_mod_write_half(0x8004b818, 0x20);
    shinka_journal_quick_menu(&cpu);
    CHECK(encounter_rate == 150 && (R(menu + 0xa4) & 1));
    fail_save = 0;
    W(menu + 0xa4, 0x401400); W(menu + 0x10, 3); W(menu + 0x58, 7);
    psx_mod_write_half(0x8004b818, 0x2000); shinka_journal_quick_menu(&cpu);
    CHECK(R(menu + 0xa0) == 0 && R(menu + 0x58) == 7); /* BACK below camera controls */
    /* All three alternates and Original survive cycling in both menu roots.
     * Persistence failure and old savestate tags retain the current preference. */
    for (unsigned mode = 0; mode < 2; ++mode) {
        W(0x8004b3f8, mode ? 0x1000 : 0x21d);
        music_palette = 0; W(menu + 0xa0, 1); W(menu + 0x58, 3);
        for (unsigned i = 0; i < 4; ++i) {
            W(menu + 0xa4, 0x401400 | (i << 24)); W(menu + 0x10, 3);
            psx_mod_write_half(0x8004b818, 0x2000); shinka_journal_quick_menu(&cpu);
            CHECK(music_palette == (i + 1) % 4 && R(menu + 0xa0) == 1 && R(menu + 0x58) == 3);
        }
        ram[0x4b87b] = 7; /* configured Left */
        W(menu + 0xa4, 0x401400); W(menu + 0x10, 3);
        psx_mod_write_half(0x8004b818, 0x80); shinka_journal_quick_menu(&cpu);
        CHECK(music_palette == 3);
        W(menu + 0xa4, 0x3401400); W(menu + 0x10, 3); fail_save = 1;
        psx_mod_write_half(0x8004b818, 0x20); shinka_journal_quick_menu(&cpu);
        CHECK(music_palette == 3 && (R(menu + 0xa4) & 1)); fail_save = 0;
        W(menu + 0xa4, 0x401400); W(menu + 0x10, 3); /* stale savestate tag */
        psx_mod_write_half(0x8004b818, 0x20); shinka_journal_quick_menu(&cpu);
        CHECK(music_palette == 3 && R(menu + 0x10) == 0 && R(menu + 0x58) == 3);
    }
    music_palette = 0; W(menu + 0xa0, 1); W(menu + 0x10, 3);
    W(menu + 0x5c, 4); W(menu + 0x58, 3); W(menu + 0xa4, 0x401400);
    psx_mod_write_half(0x8004b818, 0x2000); shinka_journal_quick_menu(&cpu);
    CHECK(music_palette == 0 && R(menu + 0x58) == 7 && R(menu + 0x10) == 0);
    W(menu + 0x5c, 5); W(menu + 0x58, 4); W(menu + 0x10, 3);
    shinka_journal_quick_menu(&cpu);
    CHECK(!view_options[0] && R(menu + 0x58) == 7 && R(menu + 0x10) == 0);
    for (unsigned mode=0; mode<2; ++mode) for (unsigned option=0;option<3;++option) {
        unsigned page=option==1 ? 1 : 6, row=option==1 ? 5 : option==2 ? 1 : 0;
        unsigned choices=option==1 ? 3 : 2;
        W(0x8004b3f8,mode ? 0x1000 : 0x21d);
        W(menu+0xa0,page);W(menu+0x5c,8);W(menu+0x58,row);
        for (unsigned i=0;i<choices;++i) {
            W(menu+0xa4,0x401400 | (view_options[0]<<26) | (view_options[1]<<27) | (view_options[2]<<19));
            W(menu+0x10,3);psx_mod_write_half(0x8004b818,0x20);
            shinka_journal_quick_menu(&cpu);
            CHECK(view_options[option]==(i+1)%choices);
            CHECK(R(menu+0x58)==row && R(menu+0xa0)==page);
        }
        W(menu+0xa4,0x401400);W(menu+0x10,3);fail_save=1;
        psx_mod_write_half(0x8004b818,0x20);
        shinka_journal_quick_menu(&cpu);
        CHECK(view_options[option]==0 && (R(menu+0xa4)&1));fail_save=0;
    }
    /* Screen view shares the expanded allocation, clears old rows and returns
     * to its own highlight in either root. A saved page cannot undo preferences. */
    for (unsigned mode=0;mode<2;++mode) for (unsigned cards=0;cards<2;++cards) {
        W(0x8004b3f8,mode ? 0x1000 : 0x21d);W(menu+0x60,cards);
        W(menu+0xa0,1);W(menu+0x5c,8);W(menu+0x58,4);
        W(menu+0x10,3);W(menu+0xa4,0x401400);
        psx_mod_write_half(0x8004b818,0x2000);shinka_journal_quick_menu(&cpu);
        CHECK(R(menu+0xa0)==6 && R(menu+0x58)==0 && R(menu+0x5c)==8);
        view_options[2]=1;W(menu+0x10,3);W(menu+0x58,1);
        shinka_journal_quick_menu(&cpu);
        CHECK(view_options[2]==1 && R(menu+0x10)==0 && R(menu+0x58)==1);
        W(menu+0x10,3);W(menu+0xa4,0x481400);W(menu+0x58,2);
        psx_mod_write_half(0x8004b818,0x2000);shinka_journal_quick_menu(&cpu);
        CHECK(R(menu+0xa0)==1 && R(menu+0x58)==4 && R(menu+0x5c)==8);
        view_options[2]=0;
    }
    /* Motion submenu works in both roots, including with no card-folder row.
     * Opening, changing rates, returning, and old BACK selection are distinct. */
    for (unsigned mode = 0; mode < 2; ++mode) for (unsigned cards = 0; cards < 2; ++cards) {
        W(0x8004b3f8, mode ? 0x1000 : 0x21d); W(menu + 0x60, cards);
        W(menu + 0xa0, 1); W(menu + 0x5c, 8); W(menu + 0x58, 6);
        W(menu + 0x10, 3); W(menu + 0xa4, 0x401400);
        psx_mod_write_half(0x8004b818, 0x2000); shinka_journal_quick_menu(&cpu);
        CHECK(R(menu + 0xa0) == 4 && R(menu + 0x58) == 0 && R(menu + 0x5c) == 8);
        for (unsigned option = 0; option < 2; ++option) {
            W(menu + 0x58, option); W(menu + 0x10, 3); W(menu + 0xa4, 0x401400);
            psx_mod_write_half(0x8004b818, 0x20); shinka_journal_quick_menu(&cpu);
            CHECK(motion_options[option] == 125 && motion_options[1-option] == 100);
            W(menu + 0x10, 3); W(menu + 0xa4, 0x401400 | (1u << (option ? 29 : 17))); fail_save = 1;
            psx_mod_write_half(0x8004b818, 0x20); shinka_journal_quick_menu(&cpu);
            CHECK(motion_options[option] == 125 && (R(menu + 0xa4) & 1)); fail_save = 0;
            W(menu + 0x10, 3); W(menu + 0xa4, 0x401400); /* stale state cannot overwrite preferences */
            psx_mod_write_half(0x8004b818, 0x20); shinka_journal_quick_menu(&cpu);
            CHECK(motion_options[option] == 125 && R(menu + 0x10) == 0);
            W(menu + 0x10, 3); W(menu + 0xa4, 0x401400 | (1u << (option ? 29 : 17)));
            psx_mod_write_half(0x8004b818, 0x80); shinka_journal_quick_menu(&cpu);
            CHECK(motion_options[option] == 100);
            /* Every choice, forward wrap and backward wrap in both roots. */
            for (unsigned index = 0; index < 4; ++index) {
                static const int values[] = {125, 150, 200, 100};
                W(menu + 0x10, 3); W(menu + 0xa4, 0x401400 | (index << (option ? 29 : 17)));
                psx_mod_write_half(0x8004b818, 0x2000); shinka_journal_quick_menu(&cpu);
                CHECK(motion_options[option] == values[index] && motion_options[1-option] == 100);
            }
            W(menu + 0x10, 3); W(menu + 0xa4, 0x401400);
            psx_mod_write_half(0x8004b818, 0x80); shinka_journal_quick_menu(&cpu);
            CHECK(motion_options[option] == 200);
            W(menu + 0x10, 3); W(menu + 0xa4, 0x401400 | (3u << (option ? 29 : 17)));
            psx_mod_write_half(0x8004b818, 0x20); shinka_journal_quick_menu(&cpu);
            CHECK(motion_options[option] == 100);
        }
        W(menu + 0x58, 2); W(menu + 0x10, 3); W(menu + 0xa4, 0x401400);
        psx_mod_write_half(0x8004b818, 0x2000); shinka_journal_quick_menu(&cpu);
        CHECK(R(menu + 0xa0) == 1 && R(menu + 0x58) == 6 && R(menu + 0x5c) == 8);
        W(menu + 0x5c, 7); W(menu + 0x10, 3);
        psx_mod_write_half(0x8004b818, 0x2000); shinka_journal_quick_menu(&cpu);
        CHECK(R(menu + 0xa0) == 1 && R(menu + 0x58) == 7);
    }
    W(menu + 0x60, 1); W(menu + 0xa0, 0); W(0x8004b3f8, 0x21d);
    W(menu + 0x58, 6);
    cpu.gpr[4] = 0x1000; cpu.gpr[17] = menu; cpu.gpr[31] = 0x80013334u;
    shinka_journal_transition(&cpu);
    CHECK(cpu.gpr[4] == 0xd01 && R(menu + 0x58) == 4);
    cpu.gpr[4] = 0x1000; shinka_journal_transition(&cpu); CHECK(cpu.gpr[4] == 0x1000);
    /* Full-screen root SETTINGS stays within the widget. DIGIVOLUTIONS must
     * finish its close animation without indexing the original submenu table. */
    W(0x8004b3f8, 0x1000); W(menu + 0xa0, 0); W(menu + 0x10, 3);
    W(menu + 0x58, 7); cpu.gpr[4] = menu;
    psx_mod_write_half(0x8004b818, 0x2000); shinka_journal_quick_menu(&cpu);
    CHECK(R(menu + 0xa0) == 1 && R(menu + 0x58) == 0);
    W(menu + 0xa0, 0); W(menu + 0x10, 3); W(menu + 0x58, 6);
    psx_mod_write_half(0x8004b818, 0xa000); shinka_journal_quick_menu(&cpu);
    CHECK(R(menu + 0xa0) == 0); /* stock navigation/confirm decides first */
    W(menu + 0x10, 4); W(menu + 0x14, 0); shinka_journal_quick_menu(&cpu);
    CHECK(R(menu + 0xa0) == 0); /* cancelling on the chart row is not entry */
    W(menu + 0x10, 4); W(menu + 0x14, 1); W(0x8005ccf0, 6);
    shinka_journal_quick_menu(&cpu);
    CHECK(R(menu + 0xa0) == 3 && R(menu + 0x14) == 0 && R(0x8005ccf0) == 4);
    W(0x80048d68, 0x21d); cpu.gpr[4] = 0x21d; cpu.gpr[31] = 0x80013318;
    shinka_journal_transition(&cpu);
    CHECK(cpu.gpr[4] == 0xd01 && R(menu + 0x58) == 4);
    W(menu + 0xa0, 0); cpu.gpr[4] = 0x21d;
    shinka_journal_transition(&cpu); CHECK(cpu.gpr[4] == 0x21d);
    W(0x8004b3f8u, 0xd01); W(0x80048d68u, 0x21d);
    cpu.gpr[4] = 0x21d; cpu.gpr[31] = 0x8008ee8cu;
    shinka_journal_transition(&cpu);
    CHECK(cpu.gpr[4] == 0x1000 && R(0x80048d68u) == 0x21d);
    CHECK(cpu.gpr[5] == 0x53484c42); /* marked return, not a stock submenu index */
    W(0x8004b3f8, 0xd00); cpu.gpr[4] = 0x21d; cpu.gpr[5] = 0;
    shinka_journal_transition(&cpu);
    CHECK(cpu.gpr[4] == 0x21d && cpu.gpr[5] == 0); /* physical lab exits normally */
    {
        const uint32_t root = 0x800e0000;
        unsigned cards, layout;
        W(root + 0x28, 0x80014274); W(root + 0x48, 0x80099894);
        W(root + 0xc, 0); W(root + 0x20, 2); cpu.gpr[4] = root;
        W(0x8004b3f8, 0x1000); W(0x8004b400, 0xd01);
        W(0x8004b404, 0); writes = 0; shinka_menu_task_ready(&cpu);
        CHECK(writes == 0); /* ordinary Status opening is unchanged */
        W(0x8004b404, 0x53484c42); W(root + 0x48, 0x80099890);
        writes = 0; shinka_menu_task_ready(&cpu); CHECK(writes == 0);
        W(root + 0x48, 0x80099894);
        for (layout = 2; layout <= 3; ++layout) for (cards = 0; cards < 2; ++cards) {
            W(root + 0x20, layout); /* original and map-travel controller allocations */
            ram[0x48f42] = (unsigned char)cards; W(root + 0x10, 0);
            W(0x8004b404, 0x53484c42); shinka_menu_task_ready(&cpu);
            CHECK(R(root + 0x10) == 1 && R(0x8005ccf0) == 5 + cards);
            CHECK(R(0x8004b404) == 0);
            writes = 0; shinka_menu_task_ready(&cpu); CHECK(writes == 0);
        }
        W(0x8005cca8, 3); W(0x8004b404, 0x53484c42);
        shinka_menu_task_ready(&cpu); CHECK(R(0x8005ccf0) == 4);
        W(0x8005cca8, 2); W(0x8004b400, 0xd00); W(0x8004b404, 0x53484c42);
        writes = 0; shinka_menu_task_ready(&cpu); CHECK(writes == 0);
    }
    W(0x8004b3f8, 0xd01);
    W(0x80055d28u, 13); W(0x80083040u, 0x27bdffe8u); W(0x8008efd0u, 0x27bdffe8u);
    W(0x8008f4b8u, 0x8008c230u); W(0x8008f4bcu, 0x80088694u); W(0x8008f4c0u, 0x80085408u);
    W(0x8008ec04u, 0xae050010u); W(0x8008ec08u, 0x8e220000u);
    W(0x8008ec0cu, 0x08023b0fu); W(0x8008ec10u, 0xac400054u);
    writes = 0; tick(); CHECK(writes == 0); /* fresh full lab remains stock */
    W(0x8008ec04u, 0x24041000u); W(0x8008ec08u, 0x0c005ae2u);
    W(0x8008ec0cu, 0x00002821u); W(0x8008ec10u, 0x08023b0fu);
    W(0x8008f4b8u, 0x80085408u); W(0x8008f4bcu, 0x80085408u);
    W(0x8008ec10u, 0xdeadbeefu);
    writes = 0; tick(); CHECK(writes == 0); /* reject whole unknown variant */
    W(0x8008ec10u, 0x08023b0fu); tick();
    CHECK(R(0x8008ec04u) == 0xae050010u && R(0x8008ec08u) == 0x8e220000u);
    CHECK(R(0x8008ec0cu) == 0x08023b0fu && R(0x8008ec10u) == 0xac400054u);
    CHECK(R(0x8008f4b8u) == 0x8008c230u && R(0x8008f4bcu) == 0x80088694u);
    W(0x8004b3f8u, 0xd00); writes = 0; tick(); CHECK(writes == 0);
    /* The old auto-confirm probe's objects remain idle for all three actions;
     * cancelling a child must let the original Select Action menu reopen. */
    W(0x8004b3f8u, 0xd01);
    W(0x80090028u, 0x80014274u); W(0x80090048u, 0x8008ed0cu);
    W(0x80090074u, 0x8008ec50u); W(0x8009000cu, 1); W(0x80090010u, 1);
    W(0x80090024u, 0x80091000u); W(0x80091000u, 0x80092000u);
    W(0x80092028u, 0x80014274u); W(0x80092048u, 0x8008a51cu);
    W(0x8009200cu, 1); W(0x80092010u, 3); W(0x8004b3fcu, 0);
    for (unsigned action = 0; action < 3; ++action) {
        W(0x80092060, action); writes = 0; tick();
        CHECK(writes == 0 && R(0x8004b3fc) == 0);
    }
    W(0x8004b3f8u, 0x700); writes = 0; tick(); CHECK(writes == 0);
    {
        const uint32_t owner=0x800a0000, wrapper=0x800b0000, root=0x800c0000, chooser=0x800d0000;
        shinka_lab_selection_reset();
        W(0x8004b3f8,0xd01);W(0x8004b3fc,0);W(0x8005ccbc,owner);
        W(0x8008ed0c,0x27bdff40);W(0x800891ac,0xac400064);
        W(owner+0x28,0x80014274);W(owner+0x48,0x80020b58);W(owner+0x20,1);
        W(owner+0x24,owner+0x100);W(owner+0x100,wrapper);
        W(wrapper+0x28,0x80014274);W(wrapper+0x48,0x80082f48);W(wrapper+0x20,1);
        W(wrapper+0x24,wrapper+0x100);W(wrapper+0x100,root);
        W(root+0x28,0x80014274);W(root+0x48,0x8008ed0c);W(root+0x20,3);
        W(root+0x24,root+0x100);W(root+0x100,chooser);
        W(chooser+0x28,0x80014274);W(chooser+0x48,0x8008a51c);W(chooser+0x20,19);
        W(chooser+0xc,1);W(chooser+0x10,15);W(chooser+0x60,2);
        W(0x80048da4,1);W(0x80048da8,5);W(0x80048dac,7);
        W(root+0x64,1);tick(); /* remember Guilmon */
        W(chooser+0x10,3);tick();W(root+0x64,0);W(chooser+0x10,10);
        writes=0;tick();CHECK(writes==1 && R(root+0x64)==1);
        W(chooser+0x10,15);tick();
        W(root+0x64,2);writes=0;tick();CHECK(writes==0); /* navigation stays responsive */
        W(chooser+0x10,3);tick();W(0x80048da4,7);W(0x80048dac,1);
        W(root+0x64,2);W(chooser+0x10,11);tick();CHECK(R(root+0x64)==0); /* identity after reorder */
        W(chooser+0x10,15);tick();
        W(chooser+0x10,3);tick();W(0x80048da4,6);W(root+0x64,0);W(chooser+0x10,10);
        writes=0;tick();CHECK(writes==0); /* absent partner: native default */
        shinka_lab_selection_reset();W(root+0x64,2);writes=0;tick();CHECK(writes==0);
        W(0x8004b3f8,0xd00);W(root+0x64,0);writes=0;tick();CHECK(writes==0);
        W(0x8004b3f8,0xd01);W(0x800891ac,0);writes=0;tick();CHECK(writes==0);
    }
    {
        const uint32_t owner=0x800a0000, wrapper=0x800b0000, root=0x800c0000, items=0x800d0000;
        const uint32_t objects[]={owner,wrapper,root,items};
        const uint32_t callbacks[]={0x80020b58,0x80083558,0x80099894,0x80091d18};
        W(0x8004b3f8,0x1000);W(0x8004b3fc,0);W(0x8005cca8,2);W(0x8005ccbc,owner);
        W(0x80091d18,0x27bdffd8);W(0x80091d1c,0xafb10014);W(0x80099894,0x27bdffa8);
        for(int i=0;i<4;++i) {
            W(objects[i]+0x28,0x80014274);W(objects[i]+0x48,callbacks[i]);
            W(objects[i]+0xc,1);W(objects[i]+0x24,objects[i]+0x100);
            W(objects[i]+0x20,i<2 ? 1 : i==2 ? 2 : 53);
        }
        W(owner+0x100,wrapper);W(wrapper+0x100,root);W(root+0x104,items);
        writes=0;CHECK(shinka_menu_items_active());CHECK(writes==0);
        W(root+0x20,3);CHECK(shinka_menu_items_active());
        /* Reused tasks, teardown and every malformed link must fail closed. */
        for(int i=0;i<4;++i) {
            W(objects[i]+0x48,0x8001270c);CHECK(!shinka_menu_items_active());W(objects[i]+0x48,callbacks[i]);
            W(objects[i]+0xc,2);CHECK(!shinka_menu_items_active());W(objects[i]+0xc,1);
            if(i<3) {
                W(objects[i]+0x24,0x801fffff);CHECK(!shinka_menu_items_active());W(objects[i]+0x24,objects[i]+0x100);
            }
        }
        W(0x8004b3fc,0x200);CHECK(!shinka_menu_items_active());W(0x8004b3fc,0);
        W(0x8004b3f8,0xd00);CHECK(!shinka_menu_items_active());W(0x8004b3f8,0x1000);
        W(0x8005cca8,3);CHECK(!shinka_menu_items_active());W(0x8005cca8,2);
        W(0x80091d1c,0);CHECK(!shinka_menu_items_active());W(0x80091d1c,0xafb10014);
        W(root+0x104,0);CHECK(!shinka_menu_items_active());W(root+0x104,items);
        shinka_lab_selection_reset();CHECK(shinka_menu_items_active()); /* load follows live owners */
        for(int kind=SHINKA_STATUS_SORT;kind<=SHINKA_STATUS_TECHNIQUES;++kind) {
            uint32_t callback=kind==SHINKA_STATUS_SORT ? 0x800980b0 : 0x80096380;
            unsigned count=kind==SHINKA_STATUS_SORT ? 35 : 45;
            W(items+0x48,callback);W(items+0x20,count);
            W(callback,0x27bdffd0);W(callback+4,0xafb3001c);
            writes=0;CHECK(shinka_menu_status_layout()==kind);CHECK(!writes);
            CHECK(!shinka_menu_items_active());
            for(int i=0;i<4;++i) {
                W(objects[i]+0xc,2);CHECK(!shinka_menu_status_layout());W(objects[i]+0xc,1);
                uint32_t cb=R(objects[i]+0x48);
                W(objects[i]+0x48,0x8001270c);CHECK(!shinka_menu_status_layout());W(objects[i]+0x48,cb);
                if(i<3) {
                    W(objects[i]+0x24,0x801fffff);CHECK(!shinka_menu_status_layout());W(objects[i]+0x24,objects[i]+0x100);
                }
            }
            W(items+0x20,count+1);CHECK(!shinka_menu_status_layout());W(items+0x20,count);
            W(callback+4,0);CHECK(!shinka_menu_status_layout());W(callback+4,0xafb3001c);
            W(root+0x104,0);W(root+0x100,items);CHECK(!shinka_menu_status_layout());
            W(root+0x100,0);W(root+0x104,items);
            W(0x8005cca8,3);CHECK(!shinka_menu_status_layout());W(0x8005cca8,2);
            W(0x8004b3fc,0x200);CHECK(!shinka_menu_status_layout());W(0x8004b3fc,0);
            shinka_lab_selection_reset();CHECK(shinka_menu_status_layout()==kind);
        }
    }
    puts("Full lab actions, partner retention, legacy restoration, root return and menu input checks passed.");
    return 0;
}
