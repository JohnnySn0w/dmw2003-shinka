/* Included before refresh_widescreen_projection in Shinka's frontend copy.
 * Called on the emulation thread; never recursively refresh the projection. */
extern "C" void shinka_view_tick(void);
extern "C" int psx_mod_game_started(void);
extern "C" void shinka_view_frontend(int wide) {
    static int previous = -1;
    static uint32_t previous_mode = 0;
    /* Fields use a different mode per area. Update the exact-state gate even
     * when the old and new scenes both request 16:9 (also after state loads). */
    const uint32_t mode = psx_read_word(0x8004b3f8u);
    if (previous == wide && previous_mode == mode) return;
    previous = wide;
    previous_mode = mode;
    const int num = wide ? 16 : 4, den = wide ? 9 : 3;
    g_video_aspect_num = num; g_video_aspect_den = den;
    g_ws_adaptive_view = false;
    g_ws_native_wide = wide;
    g_ws_projection_mode = -1;
    gpu_ws_set_gameplay_state_gate(0x8004b3f8u, &mode, 1);
    gpu_ws_set_gte_game_mode(1);
    gl_renderer_set_display_aspect(num, den);
    if (sdl_renderer) {
        g_logical_w = 480 * num * g_video_scale / den;
        SDL_RenderSetLogicalSize(sdl_renderer, g_logical_w, 480 * g_video_scale);
    }
}
