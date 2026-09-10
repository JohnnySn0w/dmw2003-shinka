#include "cpu_state.h"
#include "mod_plugins.h"

/* European SLES-03936 only; the package also guards the complete disc hash.
 * Guest state carries the entry marker so loading a state cannot leave a host
 * boolean asking an unrelated transition to open the journal. */
#define MODE 0x8004b3f8u
#define LAB 0x0d00u
#define JOURNAL 0x0d01u
#define STATUS 0x1000u
#define LAB_ROOT_RETURN 0x53484c42u
#define QUICK_MENU 0x8001270cu
#define READ psx_mod_read_word
#define WRITE psx_mod_write_word
static int enabled;
static uint32_t lab_selection_root, lab_selection_menu;
static int lab_selected_rookie = -1, lab_choosing;
extern void shinka_chart_selection_reset(void);
void shinka_lab_selection_reset(void) {
    shinka_chart_selection_reset();
    lab_selected_rookie = -1; lab_choosing = 0;
    lab_selection_root = lab_selection_menu = 0;
}
int shinka_journal_enabled(void) { return enabled; }
static int object(uint32_t p, uint32_t callback) {
    return p >= 0x80090000u && p <= 0x801eff00u && !(p & 3u)
        && READ(p + 0x28) == 0x80014274u && READ(p + 0x48) == callback;
}

#include "menu_list.inc"

static uint32_t lab_child(uint32_t p) {
    uint32_t children = READ(p + 0x24);
    return children >= 0x80090000u && children <= 0x801ffffcu && !(children & 3)
        ? READ(children) : 0;
}
/* The action menu resets root+64 before its partner selector opens. Remember
 * identity, not position: Switch Digimon can reorder the three party slots.
 * This is session UI memory; the savestate-load hook deliberately clears it. */
static void retain_lab_partner(void) {
    uint32_t root, menu, slot, i, phase;
    if (READ(MODE) != JOURNAL || READ(MODE + 4) || READ(0x80055d28) != 13
        || READ(0x8008ed0c) != 0x27bdff40 || READ(0x800891ac) != 0xac400064)
        goto inactive;
    root = READ(0x8005ccbc);
    if (!object(root, 0x80020b58) || READ(root + 0x20) != 1) goto inactive;
    root = lab_child(root);
    if (!object(root, 0x80082f48) || READ(root + 0x20) != 1) goto inactive;
    root = lab_child(root);
    if (!object(root, 0x8008ed0c) || READ(root + 0x20) != 3) goto inactive;
    menu = lab_child(root);
    if (!object(menu, 0x8008a51c) || READ(menu + 0x20) != 19
        || READ(menu + 0xc) != 1
        || READ(menu + 0x60) > 2) goto inactive;
    phase = READ(menu + 0x10);
    if (phase < 10 || phase > 15) goto inactive;
    slot = READ(root + 0x64);
    if (slot >= 3) goto inactive;
    if (!lab_choosing || root != lab_selection_root || menu != lab_selection_menu) {
        /* Phases 10/11 precede 0x80088808's summary-panel refresh. Restoring
         * only once input phase 15 begins would leave that panel stale. */
        if (phase <= 11 && lab_selected_rookie >= 0) for (i = 0; i < 3; ++i)
            if (READ(0x80048da4 + i * 4) == (uint32_t)lab_selected_rookie) {
                slot = i;
                if (READ(root + 0x64) != slot) WRITE(root + 0x64, slot);
                break;
            }
    }
    if (phase == 15) {
        i = READ(0x80048da4 + slot * 4);
        lab_selected_rookie = i < 8 ? (int)i : -1;
    }
    lab_selection_root = root; lab_selection_menu = menu; lab_choosing = 1;
    return;
inactive:
    lab_choosing = 0;
}

static int restore_lab_interface(void) {
    static const uint32_t old[] = {0xae050010u, 0x8e220000u,
                                  0x08023b0fu, 0xac400054u};
    /* Recognize the former chart-only prototype in older savestates, then
     * restore the original actions and return from each child to Select Action. */
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
        uint32_t word = old[i];
        if (READ(addr) != word) psx_mod_write_code_word(addr, word);
    }
    for (i = 0; i < 2; ++i) {
        uint32_t word = actions[i];
        if (READ(0x8008f4b8u + i * 4) != word) WRITE(0x8008f4b8u + i * 4, word);
    }
    return 1;
}

static void journal_vblank(void) {
    uint32_t mode;
    if (!enabled || !psx_mod_game_started()) return;
    shinka_rewards_tick();
    mode = READ(MODE);
    if (mode == LAB || mode == JOURNAL) restore_lab_interface();
    retain_lab_partner();
}

static void journal_activate(void) { enabled = 1; text_scratch = 0; shinka_lab_selection_reset(); shinka_rewards_activate(); }
void shinka_register_journal(void) {
    psx_mod_register_activation_plugin("shinka.evolution-journal", journal_activate);
    psx_mod_register_vblank_plugin("shinka.evolution-journal", journal_vblank);
}
