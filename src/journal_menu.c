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
static int object(uint32_t p, uint32_t callback) {
    return p >= 0x80090000u && p <= 0x801eff00u && !(p & 3u)
        && READ(p + 0x28) == 0x80014274u && READ(p + 0x48) == callback;
}

#include "menu_list.inc"

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
    shinka_rewards_tick();
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

static void journal_activate(void) { enabled = 1; manager = 0; text_scratch = 0; shinka_rewards_activate(); }
void shinka_register_journal(void) {
    psx_mod_register_activation_plugin("shinka.evolution-journal", journal_activate);
    psx_mod_register_vblank_plugin("shinka.evolution-journal", journal_vblank);
}
