#include "mod_plugins.h"
#include "reward_stock.h"

extern void shinka_rates_get(int*, int*, int*);
static int active;
static unsigned poll;
#define R psx_mod_read_word

static int dv_variant(uint32_t base) {
    uint32_t a = R(base + 0x138c), b = R(base + 0x1394);
    if (R(base + 0x1388) != 0x8e030020 || R(base + 0x1390) != 0x0060f809) return 0;
    return (a == 0 && (b == 0x00403021 || b == 0x00023040 || b == 0x00023080 || b == 0x2406000a))
        || (a == 0x00023040 && b == 0x00c23021);
}

static int reward_matches(uint32_t base) {
    unsigned offset, row;
    if (R(base) != reward_stock[0] || R(base + 4) != reward_stock[1] || !dv_variant(base)) return 0;
    /* Immutable calculation code plus every DV/BIT table cell, and only
     * recognized EXP factors. Reject revisions and other reward mods. */
    for (offset = 0x2c44; offset < 0x2e00; offset += 4)
        if (R(base + offset) != reward_stock[offset / 4]) return 0;
    for (offset = 0x3c74; offset < 0x3dd8; offset += 4)
        if (R(base + offset) != reward_stock[offset / 4]) return 0;
    for (row = 0; row < 335; ++row) {
        uint32_t pos = 0x3dd8 + row * 12, exp = reward_stock[pos / 4 + 1], actual;
        if (R(base + pos) != reward_stock[pos / 4] || R(base + pos + 8) != reward_stock[pos / 4 + 2]) return 0;
        actual = R(base + pos + 4);
        if (!exp ? actual != 0 : (actual < exp || actual > exp * 4 || actual % exp)) return 0;
    }
    return 1;
}

static void apply(uint32_t base, int battle, int dv, int fixed) {
    unsigned row;
    uint32_t a = dv == 3 && !fixed ? 0x00023040 : 0;
    uint32_t b = fixed ? 0x2406000a : dv == 1 ? 0x00403021 : dv == 2 ? 0x00023040 : dv == 3 ? 0x00c23021 : 0x00023080;
    for (row = 0; row < 335; ++row) {
        uint32_t pos = 0x3ddc + row * 12, value = reward_stock[pos / 4] * battle;
        if (R(base + pos) != value) psx_mod_write_word(base + pos, value);
    }
    if (R(base + 0x138c) != a) psx_mod_write_code_word(base + 0x138c, a);
    if (R(base + 0x1394) != b) psx_mod_write_code_word(base + 0x1394, b);
}

void shinka_rewards_refresh(void) {
    uint32_t base;
    int battle, dv, fixed;
    if (!active) return;
    shinka_rates_get(&battle, &dv, &fixed);
    if (battle < 1 || battle > 4 || dv < 1 || dv > 4 || (fixed != 0 && fixed != 10)) return;
    /* Include prefetched overlays and old savestate caches, not just the
     * currently executing overlay. Disc reads use the same committed plan. */
    for (base = 0x80082cb0; base <= 0x80200000u - sizeof(reward_stock); base += 4)
        if (reward_matches(base)) apply(base, battle, dv, fixed);
}

void shinka_rewards_tick(void) {
    if (++poll % 30 == 0) shinka_rewards_refresh();
}
void shinka_rewards_activate(void) { active = 1; poll = 29; }
