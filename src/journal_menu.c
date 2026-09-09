#include "cpu_state.h"
#include "mod_plugins.h"

/* European SLES-03936 only; the package also guards the complete disc hash.
 * Guest state carries the entry marker so loading a state cannot leave a host
 * boolean asking an unrelated transition to open the journal. */
#define MODE 0x8004b3f8u
#define LAB 0x0d00u
#define JOURNAL 0x0d01u
#define STATUS 0x1000u
#define QUICK_MENU 0x8001270cu
#define LAB_MANAGER 0x8008ed0cu
#define READ psx_mod_read_word
#define WRITE psx_mod_write_word
static int enabled;
static uint32_t manager;
static uint32_t prompt_base;
static unsigned prompt_poll = 59;

static void status_prompt(void) {
    /* Old savestates can already contain the unpatched text resource. Keep
     * the replacement within the original 28-byte string allocation. */
    static const unsigned char old[28] = {
        1,0x34,1,1,0x0f,0x3c,0x3b,0x3b,0x36,0x35,1,7,1,1,
        0x10,0x33,0x36,0x3a,0x2c,1,1,0x20,0x3b,0x28,0x3b,0x3c,0x3a,0};
    static const unsigned char label[28] = {
        0x20,0x21,0x0e,0x21,0x22,0x20,1,7,1,1,0x20,0x38,0x3c,
        0x28,0x39,0x2c,1,1,0x21,0x39,0x2c,0x2c,0,0,0,0,0,0};
    uint32_t base;
    unsigned i;
    const unsigned char *desired = enabled ? label : old;
    const unsigned char *previous = enabled ? old : label;
    if (prompt_base && READ(prompt_base) == 108 && READ(prompt_base + 80) == 700) {
        for (i = 0; i < sizeof(label); ++i)
            if (psx_mod_read_byte(prompt_base + 700 + i) != desired[i]) break;
        if (i == sizeof(label)) return;
    }
    if (++prompt_poll % 60) return;
    for (base = 0x80090000u; base < 0x801ef000u; base += 4) {
        if (READ(base) != 108 || READ(base + 4) != 436
            || READ(base + 8) != 440 || READ(base + 80) != 700) continue;
        for (i = 0; i < sizeof(old); ++i)
            if (psx_mod_read_byte(base + 700 + i) != previous[i]) break;
        if (i == sizeof(old)) {
            for (i = 0; i < sizeof(label); ++i)
                psx_mod_write_byte(base + 700 + i, desired[i]);
        } else {
            for (i = 0; i < sizeof(old); ++i)
                if (psx_mod_read_byte(base + 700 + i) != desired[i]) break;
            if (i != sizeof(old)) continue;
        }
        prompt_base = base;
    }
}

static int object(uint32_t p, uint32_t callback) {
    return p >= 0x80090000u && p <= 0x801eff00u && !(p & 3u)
        && READ(p + 0x28) == 0x80014274u && READ(p + 0x48) == callback;
}

void shinka_journal_quick_menu(CPUState *cpu) {
    uint32_t p = cpu->gpr[4], mode = READ(MODE);
    uint16_t pressed, square, confirm;
    unsigned square_bit, confirm_bit;
    if (READ(0x8005cca8u) != 2 || (mode >> 8) != 2
        || READ(0x8004b3fcu) || !object(p, QUICK_MENU)) return;
    status_prompt();
    if (!enabled || READ(p + 0xc) != 1 || READ(p + 0x10) != 3
        || READ(p + 0x58) != 4) return;
    square_bit = psx_mod_read_byte(0x8004b883u);
    confirm_bit = psx_mod_read_byte(0x8004b881u);
    if (square_bit > 15 || confirm_bit > 15) return;
    square = (uint16_t)(1u << square_bit);
    confirm = (uint16_t)(1u << confirm_bit);
    pressed = psx_mod_read_half(0x8004b818u);
    /* Simultaneous direction/confirm/back remains the stock operation. */
    if (pressed != square) return;
    WRITE(p + 0x58, 6); /* inaccessible row, consumed at the existing setter */
    psx_mod_write_half(0x8004b818u, confirm);
}

void shinka_journal_transition(CPUState *cpu) {
    uint32_t mode = READ(MODE), p = cpu->gpr[17];
    if ((mode >> 8) == 2 && cpu->gpr[4] == STATUS
        && cpu->gpr[31] == 0x80013334u && object(p, QUICK_MENU)
        && READ(p + 0x58) == 6) {
        WRITE(p + 0x58, 4);
        cpu->gpr[4] = enabled ? JOURNAL : STATUS;
    } else if (mode == JOURNAL && cpu->gpr[31] == 0x8008ee8cu
               && cpu->gpr[4] == READ(0x80048d68u)
               && (cpu->gpr[4] >> 8) == 2) {
        /* Status already saved the field context on entry. Retain it, and
         * restore its partner-selection view when the chart closes. */
        WRITE(0x8005ccf0u, 4);
        cpu->gpr[4] = STATUS;
    }
}

static int lab_variant(int remote) {
    static const uint32_t old[] = {0xae050010u, 0x8e220000u,
                                  0x08023b0fu, 0xac400054u};
    /* On chart-child completion, queue Status through the resident setter,
     * then return through the existing epilogue. The next original load is a
     * harmless delay slot; no lab action-panel/fade task is recreated. */
    static const uint32_t replacement[] = {0x24041000u, 0x0c005ae2u,
                                          0x00002821u, 0x08023b0fu};
    static const uint32_t actions[] = {0x8008c230u, 0x80088694u};
    unsigned i;
    /* Check every site before changing any site: these overlay addresses
     * also hold the field, battle, and Status programs at other times. */
    if (READ(0x80055d28u) != 13 || READ(0x80083040u) != 0x27bdffe8u
        || READ(0x8008efd0u) != 0x27bdffe8u
        || READ(0x8008f4c0u) != 0x80085408u) return 0;
    for (i = 0; i < 4; ++i) {
        uint32_t word = READ(0x8008ec04u + i * 4);
        if (word != old[i] && word != replacement[i]) return 0;
    }
    for (i = 0; i < 2; ++i) {
        uint32_t word = READ(0x8008f4b8u + i * 4);
        if (word != actions[i] && word != 0x80085408u) return 0;
    }
    for (i = 0; i < 4; ++i) {
        uint32_t addr = 0x8008ec04u + i * 4;
        uint32_t word = remote ? replacement[i] : old[i];
        if (READ(addr) != word) psx_mod_write_code_word(addr, word);
    }
    for (i = 0; i < 2; ++i) {
        uint32_t word = remote ? 0x80085408u : actions[i];
        if (READ(0x8008f4b8u + i * 4) != word) WRITE(0x8008f4b8u + i * 4, word);
    }
    return 1;
}

static void journal_vblank(void) {
    uint32_t mode, p, children, action;
    if (!enabled || !psx_mod_game_started()) return;
    mode = READ(MODE);
    if (mode != LAB && mode != JOURNAL) { manager = 0; return; }
    if (!lab_variant(mode == JOURNAL) || mode != JOURNAL) return;
    if (!object(manager, LAB_MANAGER)) {
        manager = 0;
        for (p = 0x80090000u; p < 0x801eff00u; p += 4) {
            if (object(p, LAB_MANAGER) && READ(p + 0x74) == 0x8008ec50u) {
                manager = p;
                break;
            }
        }
    }
    if (!manager || READ(manager + 0xc) != 1 || READ(manager + 0x10) != 1) return;
    children = READ(manager + 0x24);
    if (children < 0x80090000u || children > 0x801eff00u || (children & 3)) return;
    action = READ(children);
    if (action < 0x80090000u || action > 0x801eff00u || (action & 3)
        || !object(action, 0x8008a51cu) || READ(action + 0xc) != 1
        || READ(action + 0x10) != 3) return;
    if (READ(action + 0x60) == 2) {
        /* Back from the initial partner chooser: the stock UI would reopen
         * Select Action. Queue the same resident transition instead. */
        if (!READ(0x8004b3fcu)) {
            WRITE(0x8005ccf0u, 4);
            WRITE(0x8004b404u, 0);
            WRITE(0x8004b3fcu, STATUS);
        }
        return;
    }
    /* The chart is action 2. All three callbacks are temporarily chart-only,
     * so input arriving during the opening animation cannot switch partners. */
    WRITE(action + 0x60, 2);
    WRITE(action + 0x14, 0);
    WRITE(action + 0x10, 4); /* normal confirm path, including panel teardown */
}

static void journal_activate(void) { enabled = 1; manager = 0; prompt_base = 0; prompt_poll = 59; }
void shinka_register_journal(void) {
    psx_mod_register_activation_plugin("shinka.evolution-journal", journal_activate);
    psx_mod_register_vblank_plugin("shinka.evolution-journal", journal_vblank);
}
