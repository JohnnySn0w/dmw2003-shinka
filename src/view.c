#include "view.h"
#include "mod_plugins.h"

static int active_wide;
static int active_percent = 100;

void shinka_view_tick(void) {
    int battle = psx_mod_game_started() && psx_mod_read_word(0x8004b3f8u) == 0x600;
    int wide = battle && shinka_view_get(0) == 1;
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
