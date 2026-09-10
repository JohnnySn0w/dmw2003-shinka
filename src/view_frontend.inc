/* Included before refresh_widescreen_projection in Shinka's frontend copy.
 * Called on the emulation thread; never recursively refresh the projection. */
extern "C" void shinka_view_tick(void);
extern "C" int psx_mod_game_started(void);
extern "C" void shinka_view_frontend(int wide) {
    static int previous = -1;
    if (previous == wide) return;
    previous = wide;
    const int num = wide ? 16 : 4, den = wide ? 9 : 3;
    g_video_aspect_num = num; g_video_aspect_den = den;
    g_ws_adaptive_view = false;
    g_ws_native_wide = wide;
    g_ws_projection_mode = -1;
    const uint32_t battle = 0x600;
    gpu_ws_set_gameplay_state_gate(0x8004b3f8u, &battle, 1);
    gpu_ws_set_gte_game_mode(1);
    gl_renderer_set_display_aspect(num, den);
    if (sdl_renderer) {
        g_logical_w = 480 * num * g_video_scale / den;
        SDL_RenderSetLogicalSize(sdl_renderer, g_logical_w, 480 * g_video_scale);
    }
}
