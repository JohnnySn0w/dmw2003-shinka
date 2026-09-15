set(_trigger_header "#include \"${CMAKE_CURRENT_SOURCE_DIR}/src/trigger_shortcuts.h\"\nstatic ShinkaTriggerShortcuts shinka_triggers;\n")
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/src/trigger_shortcuts.inc" _trigger_code)
set(_anchors
    "static int manual_fast_forward_multiplier(void) {"
    "static void savestate_input_guard_arm(void) {"
    "static NetplayVblankEpilogue sdl_vblank_present_body(void) {"
    "    if (!g_headless) update_controller_rumble();"
    "host_keymap_down(HOST_KEYMAP_TURBO, keys, (int)SDL_GetModState()))")
foreach(_anchor IN LISTS _anchors)
    string(FIND "${_frontend_text}" "${_anchor}" _position)
    if(_position EQUAL -1)
        message(FATAL_ERROR "Review trigger shortcut hook: ${_anchor}")
    endif()
endforeach()
string(REPLACE "static int manual_fast_forward_multiplier(void) {"
    "${_trigger_header}\nstatic int manual_fast_forward_multiplier(void) {" _frontend_text "${_frontend_text}")
string(REPLACE "static void savestate_input_guard_arm(void) {"
    "static void savestate_input_guard_arm(void) {\n    shinka_triggers.reset();" _frontend_text "${_frontend_text}")
string(REPLACE "static NetplayVblankEpilogue sdl_vblank_present_body(void) {"
    "${_trigger_code}\nstatic NetplayVblankEpilogue sdl_vblank_present_body(void) {" _frontend_text "${_frontend_text}")
string(REPLACE "    if (!g_headless) update_controller_rumble();"
    "    shinka_trigger_shortcuts_poll();\n    if (!g_headless) update_controller_rumble();" _frontend_text "${_frontend_text}")
string(REPLACE "host_keymap_down(HOST_KEYMAP_TURBO, keys, (int)SDL_GetModState()))"
    "(shinka_triggers.turbo || host_keymap_down(HOST_KEYMAP_TURBO, keys, (int)SDL_GetModState())))"
    _frontend_text "${_frontend_text}")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/src/trigger_shortcuts.inc")
