#include "view.h"
#include "mod_plugins.h"
#include "menu_wide.h"

static int active_wide;
static int active_percent = 100;
int shinka_view_wide_requested(void) {
    unsigned mode = psx_mod_read_word(0x8004b3f8u);
    int started = psx_mod_game_started();
    int battle = started && mode == 0x600;
    int field = started && ((mode >= 0x200 && mode < 0x300) || shinka_menu_wide_mode(mode));
    if (started && mode == 0x1000 && !field) {
        /* The resident Start handler stores its destination row before loading
         * STSTATUS. Rows 0/1/3 are Items/Sort/Techniques. Use that guest state for presentation
         * while the overlay constructs/destroys its tasks, however long it
         * takes. Drawing patches still require the verified live task chain.
         * No host latch can leak across state loads or delay a 4:3 setting. */
        unsigned previous = psx_mod_read_word(0x8004b400u);
        unsigned row = psx_mod_read_word(0x8005ccf0u);
        field = previous >= 0x200 && previous < 0x300
            && psx_mod_read_word(0x8005cca8u) == 2
            && (row == 0 || row == 1 || row == 3);
    }
    return (battle && shinka_view_get(0) == 1)
        || (field && shinka_view_get(2) == 1);
}

void shinka_view_tick(void) {
    int battle = psx_mod_game_started() && psx_mod_read_word(0x8004b3f8u) == 0x600;
    int wide = shinka_view_wide_requested();
    int zoom = battle ? shinka_view_get(1) : 0;
    active_wide = wide;
    active_percent = zoom == 1 ? 90 : zoom == 2 ? 80 : 100;
    shinka_view_frontend(wide);
}

int shinka_view_wide_active(void) { return active_wide; }
int shinka_view_zoom_percent(void) { return active_percent; }

/* Change only the perspective contribution to SXY. Keep the game's moving
 * projection centre, depth FIFO, lighting, depth cue and H register intact.
 * A direct mode check also protects the gap before the next frontend tick
 * when an overlay or savestate changes scenes. */
void shinka_view_project(int64_t* xterm, int64_t* yterm) {
    if (active_percent == 100 || psx_mod_read_word(0x8004b3f8u) != 0x600) return;
    *xterm = *xterm * active_percent / 100;
    *yterm = *yterm * active_percent / 100;
}
