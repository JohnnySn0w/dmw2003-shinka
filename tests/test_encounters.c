#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cpu_state.h"
#include "mod_plugins.h"
#include "encounter_data.h"
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); exit(1); } } while (0)
static unsigned char ram[2097152], saved_ram[2097152];
static unsigned writes;
static int enabled = 1, rate = 100, watching;
static unsigned char* ptr(uint32_t a) {
    CHECK(a >= 0x80000000 && a < 0x80200000); return ram + (a - 0x80000000);
}
uint32_t psx_mod_read_word(uint32_t a) { uint32_t v; memcpy(&v, ptr(a), 4); return v; }
void psx_mod_write_word(uint32_t a, uint32_t v) {
    if (watching) CHECK(a == 0x80048d64 || a == 0x80042b1c
        || (a >= 0x8009b6ac && a < 0x8009b6c4));
    ++writes; memcpy(ptr(a), &v, 4);
}
int shinka_journal_enabled(void) { return enabled; }
int shinka_encounter_rate_get(void) { return rate; }
void shinka_encounter_seed(CPUState*);
void shinka_encounter_step(CPUState*);
#define R psx_mod_read_word
#define W psx_mod_write_word
static CPUState cpu;
static void field_code(void) {
    watching = 0;
    W(0x8004b3f8, 0x249); W(0x8004b3fc, 0);
    W(0x8009b69c, 0x8009252c); W(0x8009b6a0, 0x80092664); W(0x8009b6a4, 0x800927a0);
    for (unsigned i = 0; i < sizeof(encounter_code) / 4; ++i) W(0x8009252c + i * 4, encounter_code[i]);
    for (unsigned i = 0; i < 6; ++i) W(0x8009b6ac + i * 4, encounter_costs[i]);
    watching = 1;
}
static void fresh(void) {
    watching = 0; memset(ram, 0, sizeof(ram));
    W(0x80042b1c, 1); enabled = 1; rate = 100; field_code(); W(0x80048d64, 701);
}
static void prepare(void) { cpu.gpr[4] = 5; cpu.gpr[31] = 0x800926f8; shinka_encounter_step(&cpu); }
static uint32_t table(void) { return ((R(0x8009273c) & 0xffff) << 16) + (int16_t)R(0x80092744); }
static void seed(unsigned count) {
    cpu.gpr[31] = 0x80092544; shinka_encounter_seed(&cpu); W(0x80048d64, count);
}
static int walk(unsigned terrain) {
    prepare();
    int32_t count = (int32_t)R(0x80048d64) - (int32_t)R(table() + terrain * 4);
    W(0x80048d64, (uint32_t)count); return count <= 0;
}
int main(void) {
    fresh(); writes = 0; prepare(); CHECK(writes == 0 && table() == 0x8009b6ac);
    for (int percent = 50; percent <= 200; percent += 50) {
        for (unsigned terrain = 0; terrain < 6; ++terrain) {
            fresh(); rate = percent;
            unsigned steps = 0;
            do { ++steps; } while (!walk(terrain) && steps < 1000);
            unsigned expected = (1402 + encounter_costs[terrain] * (percent / 50) - 1)
                / (encounter_costs[terrain] * (percent / 50));
            CHECK(steps == expected);
        }
    }
    fresh(); rate = 50; prepare(); CHECK(R(0x80048d64) == 1402);
    seed(403); prepare(); CHECK(R(0x80048d64) == 806); /* every new roll scales once */
    prepare(); CHECK(R(0x80048d64) == 806);
    /* A battle can be queued before the original function resets its counter. */
    watching = 0; W(0x8004b3fc, 0x600); watching = 1;
    seed(301); CHECK(!(R(0x80042b1c) & 0x100));
    watching = 0; W(0x8004b3fc, 0); watching = 1;
    prepare(); CHECK(R(0x80048d64) == 602);
    seed(403); prepare();
    rate = 0; for (unsigned i = 0; i < 2000; ++i) CHECK(!walk(i % 6));
    CHECK(R(0x80048d64) == 806); /* no paused countdown or RNG progression */
    seed(0); CHECK(!walk(1)); CHECK(R(0x80048d64) == 1);
    rate = 150; seed(701); CHECK(!walk(1)); CHECK(R(0x80048d64) == 1393);
    memcpy(saved_ram, ram, sizeof(ram));
    /* All state is in saved RAM, even if CPU registers already hold the table address. */
    rate = 100; prepare(); CHECK(R(0x80048d64) == 697 && table() == 0x8009b6ac);
    memcpy(ram, saved_ram, sizeof(ram));
    CHECK(R(table() + 4) == 9);
    prepare(); CHECK(R(0x80048d64) == 697 && R(table() + 4) == 3);
    rate = 50; prepare(); CHECK(R(0x80048d64) == 1394);
    field_code(); /* opening/closing a menu reloads the original overlay */
    prepare(); CHECK(R(0x80048d64) == 1394);
    enabled = 0; prepare(); CHECK(table() == 0x8009b6ac && R(0x80048d64) == 697);
    CHECK(R(0x80042b1c) == 1);
    /* Loading old RAM cannot inherit a stale host-side countdown scale. */
    fresh(); rate = 150; prepare();
    field_code(); watching = 0; W(0x80042b1c, 1); W(0x80048d64, 701); watching = 1;
    rate = 50; prepare(); CHECK(R(0x80048d64) == 1402);
    fresh(); watching = 0; W(0x80042b1c, 0); watching = 1; rate = 200;
    writes = 0; prepare(); CHECK(writes == 0); /* preserve native encounter disable */
    fresh(); rate = 0;
    cpu.gpr[4] = 5; cpu.gpr[31] = 0x800927a0; writes = 0;
    shinka_encounter_step(&cpu); CHECK(writes == 0); /* scripted entry is untouched */
    fresh(); rate = 200; watching = 0; W(0x8009b6b0, 999); watching = 1;
    writes = 0; prepare(); CHECK(writes == 0); /* unknown terrain table rejected */
    fresh(); rate = 200; prepare(); watching = 0; W(0x8009b6b0, 3); watching = 1;
    writes = 0; prepare(); CHECK(writes == 0); /* mixed factors rejected */
    fresh(); rate = 200;
    watching = 0; W(0x8009252c, 0); watching = 1; writes = 0; prepare(); CHECK(writes == 0);
    field_code(); watching = 0; W(0x8004b3f8, 0x700); watching = 1;
    writes = 0; prepare(); CHECK(writes == 0);
    puts("Encounter frequency, pause/resume, seed, save restore, scripted-call and write guards passed.");
    return 0;
}
