/* Host-only suspension at the existing VBlank/menu pause boundaries. Never
 * advance guest devices or render while minimized. Audio already queued drains
 * naturally; its callback stays alive, as it does during the stock pause menus.
 * Do not pause merely on focus loss (controller/Steam and multitasking use it).
 */
static void shinka_minimize_wait(void) {
    const char* control = std::getenv("SHINKA_PAUSE_MINIMIZED");
    if (g_headless || !sdl_window || psx_netplay_active()
        || (control && !std::strcmp(control, "0"))
        || !(SDL_GetWindowFlags(sdl_window) & SDL_WINDOW_MINIMIZED)) return;

    extern uint64_t s_frame_count;
    const uint64_t frame = s_frame_count;
    std::fprintf(stdout, "Shinka: minimized pause frame=%llu\n", (unsigned long long)frame);
    std::fflush(stdout);
    for (auto& player : g_players) {
        if (player.handle && (player.rumble_small || player.rumble_large))
            (void)SDL_GameControllerRumble(player.handle, 0, 0, 0);
        player.rumble_small = player.rumble_large = 0;
        player.rumble_known = false;
    }
    while (SDL_GetWindowFlags(sdl_window) & SDL_WINDOW_MINIMIZED) {
        SDL_Event ev;
        while (SDL_PollEvent(&ev)) {
            if (ev.type == SDL_QUIT) {
                psx_crash_trace_set_exit_origin("sdl_window_close");
                shutdown_runtime(); /* includes memory-card flushes */
                std::exit(0);
            } else if (ev.type == SDL_CONTROLLERDEVICEREMOVED) {
                close_controller();
                refresh_player_devices();
            } else if (ev.type == SDL_CONTROLLERDEVICEADDED) {
                refresh_player_devices();
            }
            /* Consume keys used to manage the window without executing game
             * hotkeys, loading a state, or changing a menu while suspended. */
        }
        starvation_watchdog_heartbeat();
        if (SDL_GetWindowFlags(sdl_window) & SDL_WINDOW_MINIMIZED) SDL_Delay(50);
    }
    /* Wall time passed, guest time did not. Re-anchor only host pacing and
     * telemetry; preserve SPU cycles, CD deadlines, VRAM and game state. */
    s_frame_pacer = FramePacer{0};
    s_fps_last_time = 0;
    g_audio_unmute_resync = 1;
    sdl_audio_fadein_left = sdl_audio_fade_samples;
    savestate_input_guard_arm();
    std::fprintf(stdout, "Shinka: restored frame=%llu (paused at %llu)\n",
        (unsigned long long)s_frame_count, (unsigned long long)frame);
    std::fflush(stdout);
}
