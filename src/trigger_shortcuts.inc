/* After the regular pad sampler: honors keyboard/controller remapping and
 * the native active-low pad representation, including diagnostic input. */
extern "C" int shinka_menu_wide_mode(unsigned mode);
extern "C" int shinka_view_get(int option);
extern "C" int shinka_view_set(int option, int value);
static void shinka_trigger_shortcuts_poll(void) {
    bool enabled = !g_headless && host_hotkey_input_focused()
        && !psx_netplay_active() && !psx_selfcheck_resim_active()
        && !savestate_input_guard_active() && psx_mod_game_started();
    unsigned pressed = shinka_triggers.poll((uint16_t)~sio_get_pad_buttons_slot(0), enabled);
    if (pressed & ShinkaTriggerShortcuts::view) {
        unsigned mode = psx_mod_read_word(0x8004b3f8u);
        int option = mode == 0x600 ? 0
            : ((mode >= 0x200 && mode < 0x300) || shinka_menu_wide_mode(mode)) ? 2 : -1;
        if (option < 0) host_osd_push("View toggle unavailable in this scene", 1600);
        else {
            int wide = shinka_view_get(option) != 1;
            if (shinka_view_set(option, wide)) {
                refresh_widescreen_projection();
                host_osd_push(wide ? "Screen view: 16:9" : "Screen view: 4:3", 1600);
            } else host_osd_push("Could not save screen view", 1600);
        }
    }
    if (pressed & ShinkaTriggerShortcuts::speed)
        host_osd_push(shinka_triggers.turbo ? "Speedup toggled on" : "Speedup toggled off", 1600);
}
