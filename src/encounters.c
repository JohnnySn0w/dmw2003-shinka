#include "cpu_state.h"
#include "mod_plugins.h"
#include "encounter_data.h"

extern int shinka_journal_enabled(void);
extern int shinka_encounter_rate_get(void);
#define R psx_mod_read_word
#define W psx_mod_write_word
#define COUNTER 0x80048d64u
#define TABLE 0x8009b6acu

/* The original random-encounter flag is read as a 32-bit boolean. Keep its
 * enabled truth value while tagging the countdown's units and table factor in
 * its upper bits. This resident word is saved even when a menu replaces FIELDSTG.
 * The six terrain costs stay at their original RAM address and are serialized
 * with the overlay. No temporary allocation or executable instruction is patched. */
#define FLAG 0x80042b1cu
#define MARK 0x53480001u
static int marked(void) {
    uint32_t flag = R(FLAG);
    return (flag & ~0x170u) == MARK && ((flag >> 4) & 7) <= 4;
}
static void select_costs(unsigned factor) {
    unsigned i;
    for (i = 0; i < 6; ++i) if (R(TABLE + i * 4) != encounter_costs[i] * factor)
        W(TABLE + i * 4, encounter_costs[i] * factor);
}

static int field(void) {
    unsigned i;
    int original = 1, scaled = marked();
    unsigned factor = (R(FLAG) >> 4) & 7;
    if ((R(0x8004b3f8) >> 8) != 2
        || R(0x8009b69c) != 0x8009252c || R(0x8009b6a0) != 0x80092664
        || R(0x8009b6a4) != 0x800927a0) return 0;
    for (i = 0; i < sizeof(encounter_code) / 4; ++i) {
        uint32_t addr = 0x8009252c + i * 4;
        if (R(addr) != encounter_code[i]) return 0;
    }
    if (R(FLAG) != 0 && R(FLAG) != 1 && !marked()) return 0;
    for (i = 0; i < 6; ++i) {
        if (R(TABLE + i * 4) != encounter_costs[i]) original = 0;
        if (R(TABLE + i * 4) != encounter_costs[i] * factor) scaled = 0;
    }
    return original || scaled;
}

/* Only the countdown reset's RNG call marks the next stored count as stock
 * units. This hook neither draws another random number nor alters its result. */
void shinka_encounter_seed(CPUState* cpu) {
    if (cpu->gpr[31] != 0x80092544 || !field()) return;
    if (marked()) W(FLAG, R(FLAG) & ~0x100u);
}

/* The original random-check function has already passed its field/cutscene
 * gates here. Its next operation resolves terrain, then deducts the cost.
 * Scripted encounters use another entry point and never reach this hook. */
void shinka_encounter_step(CPUState* cpu) {
    uint32_t count;
    int rate, factor;
    if (cpu->gpr[31] != 0x800926f8 || cpu->gpr[4] != 5 || !field()) return;
    if (!R(FLAG)) return; /* preserve the game's own disabled encounters */
    rate = shinka_journal_enabled() ? shinka_encounter_rate_get() : 100;
    if (rate < 0 || rate > 200 || rate % 50) return;
    factor = rate / 50;
    count = R(COUNTER);
    if (count > 0x100000u) return; /* reject corrupt/unrelated countdown state */
    if (factor == 2) {
        if (marked()) {
            if (R(FLAG) & 0x100) W(COUNTER, (count + 1) / 2);
            select_costs(1);
            W(FLAG, 1);
        }
        return;
    }
    if (!marked() || !(R(FLAG) & 0x100)) { count *= 2; W(COUNTER, count); }
    if (!factor && !count) W(COUNTER, 1); /* zero seed cannot fire while paused */
    W(FLAG, MARK | 0x100u | ((unsigned)factor << 4));
    select_costs((unsigned)factor);
}
