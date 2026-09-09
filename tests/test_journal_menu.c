#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cpu_state.h"
#include "mod_plugins.h"

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
void shinka_journal_transition(CPUState *cpu);
void shinka_register_journal(void);
#define W psx_mod_write_word
#define R psx_mod_read_word

static int battle_rate = 3, dv_rate = 1, fixed_rate = 10, fail_save;
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
    W(0x8004b3fcu, 0x700);
    writes = 0; shinka_journal_quick_menu(&cpu); CHECK(writes == 0);
    W(0x8004b3fcu, 0); W(menu + 0x20, 0x2d); W(menu + 0x60, 1);
    W(menu + 0x24, 0x80100000);
    CHECK(shinka_menu_slot(menu, 0x80100020) == 0x80100020);
    CHECK(shinka_menu_slot(menu, 0x80100024) == 0x801000ac);
    CHECK(shinka_menu_slot(menu, 0x80100028) == 0x801000b0);
    W(menu + 0x58, 4); shinka_journal_quick_menu(&cpu);
    CHECK(R(menu + 0x58) == 4); /* Square no longer changes STATUS */
    W(menu + 0x58, 7); psx_mod_write_half(0x8004b818, 0xa000);
    shinka_journal_quick_menu(&cpu);
    CHECK(R(menu + 0xa0) == 1 && R(menu + 0x58) == 0 && R(menu + 0x10) == 0);
    W(menu + 0xa4, 0x11300); W(menu + 0x10, 3); ram[0x4b879] = 5;
    psx_mod_write_half(0x8004b818, 0x20); shinka_journal_quick_menu(&cpu);
    CHECK(battle_rate == 4); CHECK(R(menu + 0x10) == 0);
    W(menu + 0xa4, 0x11400); W(menu + 0x10, 3); W(menu + 0x58, 1); psx_mod_write_half(0x8004b818, 0x20);
    shinka_journal_quick_menu(&cpu); CHECK(dv_rate == 1 && fixed_rate == 0);
    /* Combined confirm inputs must never send the SETTINGS index to Status.
     * A persistence failure keeps the old rates and makes the error visible. */
    W(menu + 0xa4, 0x1400); W(menu + 0x10, 3); fail_save = 1;
    psx_mod_write_half(0x8004b818, 0xa020); shinka_journal_quick_menu(&cpu);
    CHECK(dv_rate == 1 && (R(menu + 0xa4) & 1) && R(menu + 0x10) == 0);
    fail_save = 0;
    W(menu + 0x58, 6);
    cpu.gpr[4] = 0x1000; cpu.gpr[17] = menu; cpu.gpr[31] = 0x80013334u;
    shinka_journal_transition(&cpu);
    CHECK(cpu.gpr[4] == 0xd01 && R(menu + 0x58) == 4);
    cpu.gpr[4] = 0x1000; shinka_journal_transition(&cpu); CHECK(cpu.gpr[4] == 0x1000);
    W(0x8004b3f8u, 0xd01); W(0x80048d68u, 0x21d);
    cpu.gpr[4] = 0x21d; cpu.gpr[31] = 0x8008ee8cu;
    shinka_journal_transition(&cpu);
    CHECK(cpu.gpr[4] == 0x1000 && R(0x80048d68u) == 0x21d);
    W(0x80055d28u, 13); W(0x80083040u, 0x27bdffe8u); W(0x8008efd0u, 0x27bdffe8u);
    W(0x8008f4b8u, 0x8008c230u); W(0x8008f4bcu, 0x80088694u); W(0x8008f4c0u, 0x80085408u);
    W(0x8008ec04u, 0xae050010u); W(0x8008ec08u, 0x8e220000u);
    W(0x8008ec0cu, 0x08023b0fu); W(0x8008ec10u, 0xac400054u);
    W(0x8008ec10u, 0xdeadbeefu);
    writes = 0; tick(); CHECK(writes == 0); /* reject whole unknown variant */
    W(0x8008ec10u, 0xac400054u); tick();
    CHECK(R(0x8008ec04u) == 0x24041000u && R(0x8008f4b8u) == 0x80085408u);
    W(0x8004b3f8u, 0xd00); tick();
    CHECK(R(0x8008ec04u) == 0xae050010u && R(0x8008f4b8u) == 0x8008c230u);
    /* Enter via the normal close animation; cancelling the partner chooser
     * must not loop back into it or overwrite an already queued transition. */
    W(0x8004b3f8u, 0xd01);
    W(0x80090028u, 0x80014274u); W(0x80090048u, 0x8008ed0cu);
    W(0x80090074u, 0x8008ec50u); W(0x8009000cu, 1); W(0x80090010u, 1);
    W(0x80090024u, 0x80091000u); W(0x80091000u, 0x80092000u);
    W(0x80092028u, 0x80014274u); W(0x80092048u, 0x8008a51cu);
    W(0x8009200cu, 1); W(0x80092010u, 3);
    tick(); CHECK(R(0x80092060u) == 2 && R(0x80092010u) == 4);
    CHECK(R(0x80092054u) == 0); /* confirmation flag follows actual animation */
    W(0x80092010u, 3); W(0x8004b3fcu, 0x700);
    tick(); CHECK(R(0x8004b3fcu) == 0x700);
    W(0x8004b3fcu, 0); tick();
    CHECK(R(0x8004b3fcu) == 0x1000 && R(0x80048d68u) == 0x21d);
    W(0x8004b3f8u, 0x700); writes = 0; tick(); CHECK(writes == 0);
    puts("Journal context, input, return, revision rejection and restore checks passed.");
    return 0;
}
