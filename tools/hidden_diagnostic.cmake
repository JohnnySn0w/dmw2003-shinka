# Keep a real renderer for unattended GPU captures without opening a visible
# window. Headless mode does not create the native-wide render surface.
set(_hidden_anchor "    win_flags |= psx_fullscreen_flag_for_mode(g_fullscreen);")
string(FIND "${_frontend_text}" "${_hidden_anchor}" _hidden_pos)
if(_hidden_pos EQUAL -1)
    message(FATAL_ERROR "Review pinned diagnostic window creation site")
endif()
string(REPLACE "${_hidden_anchor}" "${_hidden_anchor}
    const char* hidden_diagnostic = std::getenv(\"SHINKA_DIAGNOSTIC_HIDDEN\");
    if (hidden_diagnostic && std::strcmp(hidden_diagnostic, \"1\") == 0) {
        win_flags &= ~(SDL_WINDOW_SHOWN | SDL_WINDOW_FULLSCREEN_DESKTOP);
        win_flags |= SDL_WINDOW_HIDDEN;
    }" _frontend_text "${_frontend_text}")
