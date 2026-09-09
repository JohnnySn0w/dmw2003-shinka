#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "reward_stock.h"

static unsigned char ram[2097152];
static unsigned writes;
static int battle = 1, dv = 1, fixed;
#define CHECK(c) do { if (!(c)) { fprintf(stderr, "line %d: %s\n", __LINE__, #c); exit(1); } } while (0)
uint32_t psx_mod_read_word(uint32_t addr) { uint32_t value; memcpy(&value, ram + (addr & 0x1fffff), 4); return value; }
void psx_mod_write_word(uint32_t addr, uint32_t value) { memcpy(ram + (addr & 0x1fffff), &value, 4); ++writes; }
void psx_mod_write_code_word(uint32_t addr, uint32_t value) { psx_mod_write_word(addr, value); }
void shinka_rates_get(int* b, int* d, int* f) { *b = battle; *d = dv; *f = fixed; }
void shinka_rewards_activate(void);
void shinka_rewards_refresh(void);

int main(void) {
    const uint32_t live = 0x82cb0, cached = 0xbbc8c;
    unsigned factor, mode, row;
    memcpy(ram + live, reward_stock, sizeof(reward_stock));
    memcpy(ram + cached, reward_stock, sizeof(reward_stock));
    shinka_rewards_refresh(); CHECK(writes == 0);
    shinka_rewards_activate();
    for (factor = 1; factor <= 4; ++factor) for (mode = 0; mode < 5; ++mode) {
        battle = factor; dv = mode == 4 ? 1 : mode + 1; fixed = mode == 4 ? 10 : 0;
        shinka_rewards_refresh();
        for (row = 0; row < 335; ++row) {
            uint32_t offset = 0x3dd8 + row * 12;
            CHECK(psx_mod_read_word(live + offset + 4) == reward_stock[offset / 4 + 1] * factor);
            CHECK(psx_mod_read_word(cached + offset + 4) == reward_stock[offset / 4 + 1] * factor);
            CHECK(psx_mod_read_word(live + offset) == reward_stock[offset / 4]);
            CHECK(psx_mod_read_word(cached + offset + 8) == reward_stock[offset / 4 + 2]);
        }
        CHECK(psx_mod_read_word(live + 0x1394) == (mode == 4 ? 0x2406000a : mode == 3 ? 0x00023080
            : mode == 2 ? 0x00c23021 : mode == 1 ? 0x00023040 : 0x00403021));
        writes = 0; shinka_rewards_refresh(); CHECK(writes == 0); /* idempotent */
    }
    /* A restored vanilla cache follows current settings. A revised overlay
     * must be rejected without partially scaling any other table cell. */
    memcpy(ram + cached, reward_stock, sizeof(reward_stock));
    shinka_rewards_refresh(); CHECK(psx_mod_read_word(cached + 0x1394) == 0x2406000a);
    ram[cached + 0x2c48] ^= 1; ram[live + 0x3dd8] ^= 1;
    battle = 1; dv = 1; fixed = 0; writes = 0;
    shinka_rewards_refresh(); CHECK(writes == 0);
    puts("Live and cached rewards: all 20 rate combinations, restore, idempotence and revision rejection passed.");
    return 0;
}
