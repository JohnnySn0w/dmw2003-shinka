#include "cpu_state.h"
#include "mod_plugins.h"
#include "menu_wide.h"

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
static uint32_t wide_menu_root, wide_menu_mode;
static uint32_t lab_selection_root, lab_selection_menu;
static int lab_selected_rookie = -1, lab_choosing;
extern void shinka_chart_selection_reset(void);
void shinka_lab_selection_reset(void) {
    wide_menu_root = 0; wide_menu_mode = 0;
    shinka_menu_animation_reset();
    shinka_chart_selection_reset();
    lab_selected_rookie = -1; lab_choosing = 0;
    lab_selection_root = lab_selection_menu = 0;
}
int shinka_journal_enabled(void) { return enabled; }
static int object(uint32_t p, uint32_t callback) {
    return p >= 0x80090000u && p <= 0x801eff00u && !(p & 3u)
        && READ(p + 0x28) == 0x80014274u && READ(p + 0x48) == callback;
}

int shinka_menu_root_active(void) {
    uint32_t p = wide_menu_root, mode = READ(MODE);
    /* Render lifetime, not input readiness: phases 4..6 hide the controls;
     * lifecycle 2 runs the closing wipe before lifecycle 3 releases the task.
     * A cancelled Status root also spans the final release-to-field handoff;
     * a confirmed submenu must stop here so its own layout can take over.
     * Its layout/aspect must survive that interval regardless of cursor row.
     * A queued mode doesn't hide the old screen until MODE actually changes. */
    return p && mode == wide_menu_mode && ((mode >> 8) == 2 || mode == STATUS)
        && object(p, QUICK_MENU) && READ(p + 0x20) == 0x2d
        && (READ(p + 0xc) <= 2 || (mode == STATUS && READ(p + 0xc) == 3 && !READ(p + 0x14)))
        && READ(p + 0x10) <= 7 && READ(p + 0xa0) != 5;
}

#include "menu_list.inc"

static uint32_t lab_child(uint32_t p) {
    uint32_t children = READ(p + 0x24);
    return children >= 0x80090000u && children <= 0x801ffffcu && !(children & 3)
        ? READ(children) : 0;
}
static uint32_t status_page(void) {
    uint32_t p, children;
    /* A queued destination does not end this overlay's render lifetime. Its
     * verified owner chain still supplies panels during the closing frames. */
    if (READ(MODE) != STATUS
        || READ(0x8005cca8) != 2 /* verified English layout */
        || READ(0x80099894) != 0x27bdffa8) return 0;
    /* Follow the live owner chain, not a RAM scan or a pointer retained across
     * savestate loads. Other Status children use a different final callback. */
    p = READ(0x8005ccbc);
    if (!object(p, 0x80020b58) || READ(p + 0x20) != 1 || READ(p + 0xc) > 1) return 0;
    p = lab_child(p);
    if (!object(p, 0x80083558) || READ(p + 0x20) != 1 || READ(p + 0xc) > 1) return 0;
    p = lab_child(p);
    if (!object(p, 0x80099894) || READ(p + 0xc) > 1
        || READ(p + 0x20) < 2 || READ(p + 0x20) > 3) return 0;
    children = READ(p + 0x24);
    if (children < 0x80090000 || children > 0x801ffff8 || (children & 3)) return 0;
    p = READ(children + 4);
    return p;
}
static int map_page(uint32_t p) {
    if (!object(p, 0x8009913c) || READ(p + 0x20) != 1 || READ(p + 0xc) > 1
        || READ(0x8009913c) != 0x27bdffe0 || READ(0x80099140) != 0xafb10014) return 0;
    int pan = (int32_t)READ(p + 0x90);
    return pan >= -72 && pan <= 0;
}
int shinka_menu_map_pan(void) {
    uint32_t p = status_page();
    return map_page(p) ? (int32_t)READ(p + 0x90) : 0;
}
static int live_page(uint32_t p, uint32_t callback, unsigned count, uint32_t prologue) {
    return object(p, callback) && READ(p + 0x20) == count && READ(p + 0xc) <= 1
        && READ(callback) == prologue;
}
static int extra_menu_layout(unsigned mode) {
    uint32_t p, child, children;
    if ((mode != 0x400 && mode != 0x1200 && mode != LAB && mode != JOURNAL)
        || READ(0x8005cca8) != 2) return 0;
    p = READ(0x8005ccbc);
    if (!object(p, 0x80020b58) || READ(p + 0x20) != 1 || READ(p + 0xc) > 1) return 0;
    p = lab_child(p);
    uint32_t owner = mode == 0x400 ? 0x800831f0 : mode == 0x1200 ? 0x80083ad8 : 0x80082f48;
    if (!object(p, owner) || READ(p + 0x20) != 1 || READ(p + 0xc) > 1) return 0;
    p = lab_child(p);
    if (mode == 0x1200)
        return live_page(p, 0x80085540, 19, 0x27bdffe0) ? SHINKA_CARD_ALBUM : 0;
    if (mode == 0x400) {
        /* The folder owner sleeps in lifecycle 2 while its editor runs. */
        if (!object(p, 0x80089e98) || READ(p + 0x20) != 27
            || READ(p + 0xc) > 2 || READ(0x80089e98) != 0x27bdffe0) return 0;
        child = lab_child(p);
        if (live_page(child, 0x80086574, 53, 0x27bdffe0)) {
            children = READ(child + 0x24);
            if (children >= 0x80090000 && children <= 0x801fff2c && !(children & 3)
                && live_page(READ(children + 52*4), 0x800888b0, 0, 0x27bdffe0))
                return SHINKA_FOLDER_CARDS;
            /* Native 800857a0..800857b4 toggles this explanation flag.
             * The earlier +0x68 field is animated and cannot identify it. */
            return READ(child + 0x43c) == 1 ? SHINKA_FOLDER_EXPLAIN : SHINKA_FOLDER_EDIT;
        }
        return READ(p + 0xc) <= 1 ? SHINKA_FOLDER_SELECT : 0;
    }
    if (READ(0x80055d28) != 13 || !live_page(p, 0x8008ed0c, 3, 0x27bdff40)) return 0;
    children = READ(p + 0x24);
    if (children < 0x80090000 || children > 0x801ffff4 || (children & 3)) return 0;
    child = READ(children + 4);
    /* Page turns sleep the chart owner (lifecycle 2) while its children keep
     * drawing the title and shoulder prompts. Keep that same layout active. */
    if (object(child, 0x800842f4) && READ(child + 0x20) == 7
        && READ(child + 0xc) <= 2 && READ(0x800842f4) == 0x27bdffc8) return SHINKA_LAB_CHART;
    if (live_page(child, 0x800885ec, 24, 0x27bdffe0)) {
        children = READ(child + 0x24);
        if (children < 0x80090000 || children > 0x801fffa0 || (children & 3)) return 0;
        if (live_page(READ(children + 21*4), 0x8008e8d0, 28, 0x27bdff80)) return SHINKA_LAB_TECHNIQUES;
        if (live_page(READ(children + 23*4), 0x8008c960, 23, 0x27bdff30)) return SHINKA_LAB_LOAD;
    }
    return SHINKA_LAB;
}
/* Field children 4/5 own the inn and area-entry card. Follow the live chain
 * so ordinary NPC speech and unrelated uses of the same font stay untouched. */
static int field_overlay_layout(unsigned mode) {
    if (mode < 0x200 || mode >= 0x300 || READ(0x8005cca8) != 2) return 0;
    uint32_t p = READ(0x8005ccbc), children;
    if (!live_page(p, 0x80020b58, 1, 0x27bdffe0)) return 0;
    p = lab_child(p);
    if (!live_page(p, 0x800874d0, 3, 0x27bdffe0)) return 0;
    p = lab_child(p);
    if (!live_page(p, 0x8008aa10, 31, 0x27bdffc0)) return 0;
    children = READ(p + 0x24);
    if (children < 0x80090000 || children > 0x801fff80 || (children & 3)) return 0;
    p = READ(children + 5*4);
    if (object(p, 0x80087974) && READ(p + 0x20) == 2
        && READ(p + 0xc) <= 2 && READ(0x80087974) == 0x27bdffd0) return SHINKA_FIELD_ENTRY;
    p = READ(children + 4*4);
    return live_page(p, 0x800119a8, 8, 0x27bdff38) ? SHINKA_FIELD_INN : 0;
}

int shinka_menu_status_layout(void) {
    unsigned mode = READ(MODE);
    if (mode >= 0x200 && mode < 0x300) return field_overlay_layout(mode);
    if (mode != STATUS) return extra_menu_layout(mode);
    uint32_t p = status_page(), children;
    if (!p) return SHINKA_STATUS_NONE;
    if (map_page(p)) return SHINKA_STATUS_MAP;
    if (live_page(p, 0x80084a98, 40, 0x27bdffd0)) return SHINKA_STATUS_FOLDERS;
    if (object(p, 0x80091d18) && READ(p + 0x20) == 53 && READ(p + 0xc) <= 1
        && READ(0x80091d18) == 0x27bdffd8 && READ(0x80091d1c) == 0xafb10014)
        return SHINKA_STATUS_ITEMS;
    /* These pages occupy child slot 1. Slot 0 is null while a page is open
     * and becomes the Start root on return. Recognize callback and layout
     * together, not the last selected row. */
    if (object(p, 0x800980b0) && READ(p + 0x20) == 35 && READ(p + 0xc) <= 1
        && READ(0x800980b0) == 0x27bdffd0 && READ(0x800980b4) == 0xafb3001c)
        return SHINKA_STATUS_SORT;
    if (object(p, 0x80096380) && READ(p + 0x20) == 45 && READ(p + 0xc) <= 1
        && READ(0x80096380) == 0x27bdffd0 && READ(0x80096384) == 0xafb3001c)
        return SHINKA_STATUS_TECHNIQUES;
    if (object(p, 0x8008e744) && READ(p + 0x20) == 68 && READ(p + 0xc) <= 1
        && READ(0x8008e744) == 0x27bdffd0 && READ(0x8008e748) == 0xafb3001c) {
        unsigned phase = READ(p + 0x10);
        /* Cancel from the partner chooser runs the 50..56 closing sequence.
         * Its footer survives into that sequence; treating it as the detail
         * page would split the caption between the left and right columns. */
        if (phase <= 12 || (phase >= 50 && phase <= 56)) return SHINKA_STATUS_CHARACTER_SELECT;
        /* The two actions share this owner. Its action index survives while
         * their nested selectors are open, including equipment comparison. */
        if (READ(p + 0x10) >= 18 && READ(p + 0x10) <= 23) {
            if (READ(p + 0x74) == 1) return SHINKA_STATUS_EQUIPMENT;
            /* Child 67 owns the form/action/technique pages. Its native slide
             * moves the detail block from 0 to -34 when opening techniques
             * (8008a8f4), then back on return. Root phase 21 covers all three;
             * a text object's flags can remain set while its parent hides it. */
            children = READ(p + 0x24);
            if (children < 0x80090000 || children > 0x801ffef0 || (children & 3)) return 0;
            uint32_t detail = READ(children + 67 * 4);
            if (!object(detail, 0x8008b3c8) || READ(detail + 0x20) != 36
                || READ(detail + 0xc) > 1 || READ(detail + 0x50) != p
                || READ(0x8008b3c8) != 0x27bdffe0 || READ(0x8008b3cc) != 0xafb10014)
                /* The parent remains visible for one frame before its child
                 * is constructed and after it is released. Keep that verified
                 * parent layout; do not briefly draw it at native x positions. */
                return SHINKA_STATUS_CHARACTER;
            int slide = (int32_t)READ(detail + 0x8c);
            if (slide < -34 || slide > 0) return 0;
            return slide < 0
                ? SHINKA_STATUS_CHARACTER_TECHNIQUES : SHINKA_STATUS_DIGIVOLVE;
        }
        return SHINKA_STATUS_CHARACTER;
    }
    return SHINKA_STATUS_NONE;
}
int shinka_menu_items_active(void) { return shinka_menu_status_layout() == SHINKA_STATUS_ITEMS; }
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
