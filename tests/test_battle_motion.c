#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "battle_motion_data.h"
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); exit(1); } } while (0)
static unsigned char memory[0x200000], before[0x200000];
static unsigned reads;
static int rates[2] = {100, 100};
int shinka_motion_get(int option) { return rates[option]; }
int shinka_battle_motion_category(uint32_t);
void shinka_battle_motion_reset(void);
void shinka_battle_motion_restart(uint32_t);
uint32_t shinka_battle_motion_load(uint32_t, uint32_t);
#define MODEL 0x80100000u
#define GROUP 0x800b0600u
static void put(uint32_t p, uint32_t value) { memcpy(memory + p - 0x80000000u, &value, 4); }
uint32_t psx_mod_read_word(uint32_t p) {
    uint32_t value;
    CHECK(!(p & 3) && p >= 0x80000000u && p <= 0x801ffffcu);
    ++reads; memcpy(&value, memory + p - 0x80000000u, 4); return value;
}
uint32_t shinka_battle_motion_step(uint32_t, uint32_t, unsigned);
static void entry(unsigned index, uint16_t value) {
    memcpy(memory + MODEL - 0x80000000u + 0xa4 + index * 2, &value, 2);
}
static void object(uint32_t p, uint32_t cb, uint32_t child) {
    const uint32_t methods[] = {0x80014274, 0x80014288, 0x80014298, 0x800142a4,
        0x800142ac, 0x800142c8, 0x800142e0, 0x800142f4};
    for (unsigned i = 0; i < 8; ++i) put(p + 0x28 + i * 4, methods[i]);
    put(p + 0x48, cb); put(p + 0x20, child ? 1 : 0);
    put(p + 0x24, p + 0x1c0); put(p + 0x1c0, child);
}
static void fresh(void) {
    shinka_battle_motion_reset();
    memset(memory, 0, sizeof(memory));
    put(0x8004b3f8, 0x600); put(0x8005ccbc, 0x800b0000);
    object(0x800b0000, 0x80020b58, 0x800b0200);
    object(0x800b0200, 0x80087070, 0x800b0400);
    object(0x800b0400, 0x800a6c44, GROUP);
    object(GROUP, 0x80087bb0, MODEL); put(GROUP + 0x20, 8);
    object(MODEL, 0x80083e0c, 0);
    put(MODEL + 0x64, GROUP + 0x50); put(GROUP + 0x50, 1);
    put(MODEL + 0x80, 10); put(MODEL + 0xa0, 30);
    for (unsigned i = 0; i < sizeof(battle_motion_code) / 4; ++i)
        put(0x80083a54 + i * 4, battle_motion_code[i]);
    for (unsigned i = 0; i < 30; ++i) entry(i, (uint16_t)(i + 1));
    entry(29, 0xffff);
    reads = 0;
}
static uint32_t step(unsigned delta, unsigned factor) {
    uint32_t result;
    memcpy(before, memory, sizeof(memory));
    result = shinka_battle_motion_step(MODEL, delta, factor);
    CHECK(!memcmp(before, memory, sizeof(memory)));
    return result;
}
static unsigned advance(uint32_t model, unsigned delta, unsigned percent) {
    unsigned position = psx_mod_read_word(model + 0x80);
    unsigned result = shinka_battle_motion_step(model, delta, percent);
    put(model + 0x80, position + result);
    return result;
}
static void long_clip(void) {
    fresh(); put(MODEL + 0xa0, 1000); entry(29, 30);
}
static void fractions(void) {
    for (unsigned rate = 125; rate <= 150; rate += 25) {
        unsigned elapsed = 0, travelled = 0;
        long_clip();
        for (unsigned i = 0; i < 80; ++i) {
            unsigned delta = i % 4 + 1;
            elapsed += delta; travelled += advance(MODEL, delta, rate);
            CHECK(travelled == elapsed * rate / 100);
        }
    }
    /* Interleaving actors cannot share a fraction. */
    long_clip();
    memcpy(memory + 0x110000, memory + 0x100000, 0x2634);
    put(GROUP + 0x1c4, 0x80110000); put(0x80110064, GROUP + 0x9c); put(GROUP + 0x9c, 1);
    for (unsigned i = 0; i < 4; ++i) {
        CHECK(advance(MODEL, 1, 125) == (i == 3 ? 2u : 1u));
        CHECK(advance(0x80110000, 1, 150) == (i % 2 ? 2u : 1u));
    }
    /* Same-clip restart, same-position restore, rate change, identity changes,
     * discontinuity and guard failures all discard an accumulated fraction. */
    for (unsigned kind = 0; kind < 9; ++kind) {
        long_clip(); CHECK(advance(MODEL, 1, 150) == 1);
        switch (kind) {
        case 0: shinka_battle_motion_restart(MODEL); break;
        case 1: shinka_battle_motion_reset(); break;
        case 2: CHECK(advance(MODEL, 1, 100) == 1); break;
        case 3: put(MODEL + 0x74, 0x800e0000); break;
        case 4: put(MODEL + 0x78, 2); break;
        case 5: put(MODEL + 0x80, 20); break;
        case 6: put(0x80083d30, 0); CHECK(step(1, 150) == 1);
            put(0x80083d30, battle_motion_code[(0x80083d30-0x80083a54)/4]); break;
        case 7: CHECK(step(5, 150) == 5); break;
        case 8: put(MODEL + 0xa0, 999); break;
        }
        CHECK(advance(MODEL, 1, 150) == 1);
    }
    long_clip(); CHECK(advance(MODEL, 1, 150) == 1);
    CHECK(advance(MODEL, 1, 125) == 1); /* changing directly between fractions */
    /* Preserve only the fractional remainder through a native loop jump;
     * the integer overshoot must never skip a marker or trigger an extra loop. */
    long_clip(); entry(11, 0x8000); put(MODEL + 0xd24 + 20, 10u << 16);
    CHECK(step(1, 150) == 1); /* native jumps back to 10 */
    entry(11, 12); CHECK(step(1, 150) == 2);
    for (unsigned marker = 11; marker <= 16; ++marker) {
        long_clip(); entry(marker, 0xffff); CHECK(step(4, 150) == marker - 10);
    }
}
int main(void) {
    fresh(); CHECK(step(3, 100) == 3 && reads == 0);
    CHECK(step(3, 0) == 3 && step(3, 99) == 3 && reads == 0);
    CHECK(step(0, 200) == 0 && step(5, 200) == 5 && reads == 0);
    for (unsigned d = 1; d <= 4; ++d) CHECK(step(d, 200) == d * 2);
    /* Both marker positions, both halfword lanes, and intervening interpolation
     * entries: only exact 8000/ffff values end the bounded scan. */
    for (unsigned i = 11; i <= 18; ++i) {
        fresh(); entry(i, 0xffff); CHECK(step(4, 200) == i - 10);
        fresh(); entry(i, 0x8000); CHECK(step(4, 200) == i - 10);
        fresh(); entry(i, 0x8100); CHECK(step(4, 200) == 8);
    }
    fresh(); put(MODEL + 0x80, 27); CHECK(step(4, 200) == 2);
    fresh(); entry(12, 0x8000); put(MODEL + 0xd24 + 24, 30); CHECK(step(4, 200) == 4);
    fresh(); put(MODEL + 0xa0, 1601); CHECK(step(2, 200) == 2);
    fresh(); put(MODEL + 0x80, 30); CHECK(step(2, 200) == 2);
    fresh(); put(MODEL + 0x7c, 1); CHECK(step(2, 200) == 2);
    fresh(); put(0x8004b3f8, 0x200); CHECK(step(2, 200) == 2);
    fresh(); put(0x80083d30, 0); CHECK(step(2, 200) == 2);
    fresh(); put(GROUP + 0x1c0, 0); CHECK(step(2, 200) == 2); /* scenery/detached */
    fresh(); put(MODEL + 0x64, GROUP + 0x54); CHECK(step(2, 200) == 2);
    fresh(); put(MODEL + 0x64, 0x801ffffc); CHECK(step(2, 200) == 2);
    fresh(); put(GROUP + 0x50, 0); CHECK(step(2, 200) == 2);
    fresh(); put(GROUP + 0x28, 0); CHECK(step(2, 200) == 2);
    fresh(); put(0x800b0000 + 0x20, 17); CHECK(step(2, 200) == 2);
    fresh(); put(0x800b0000 + 0x24, 0x801ffffe); CHECK(step(2, 200) == 2);
    fresh(); CHECK(shinka_battle_motion_step(0xfffffffcu, 2, 200) == 2);
    /* Changes take effect immediately; no cached owner/code match survives a
     * restore or overlay replacement. A valid image works again after rejection. */
    fresh(); CHECK(step(2, 200) == 4);
    put(0x8005ccbc, 0); CHECK(step(2, 200) == 2);
    fresh(); CHECK(step(2, 200) == 4);
    /* Independent rates follow each actor's default pose, not clip-ID ranges.
     * Action clips include reactions and victory; settings never multiply. */
    fresh(); put(MODEL + 0x78, 1);
    CHECK(shinka_battle_motion_category(MODEL) == 0);
    CHECK(shinka_battle_motion_load(MODEL, 2) == 2);
    rates[0] = 200; CHECK(shinka_battle_motion_load(MODEL, 2) == 4);
    put(MODEL + 0x78, 39);
    CHECK(shinka_battle_motion_category(MODEL) == 1);
    CHECK(shinka_battle_motion_load(MODEL, 2) == 2);
    rates[1] = 200; CHECK(shinka_battle_motion_load(MODEL, 2) == 4);
    rates[0] = 100; CHECK(shinka_battle_motion_load(MODEL, 2) == 4);
    put(GROUP + 0x68, 38); CHECK(shinka_battle_motion_category(MODEL) == 0);
    CHECK(shinka_battle_motion_load(MODEL, 2) == 2);
    put(MODEL + 0x64, 0xfffffffc); CHECK(shinka_battle_motion_category(MODEL) == -1);
    fractions();
    puts("battle motion guards and marker handling passed");
    return 0;
}
