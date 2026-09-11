file(READ "${CMAKE_CURRENT_SOURCE_DIR}/src/minimize_pause.inc" _minimize_code)
set(_minimize_anchor "static void rewind_pause_present(void) {")
string(FIND "${_frontend_text}" "${_minimize_anchor}" _minimize_pos)
if(_minimize_pos EQUAL -1)
    message(FATAL_ERROR "Review minimized pause helper placement")
endif()
string(REPLACE "${_minimize_anchor}" "${_minimize_code}\n${_minimize_anchor}" _frontend_text "${_frontend_text}")
foreach(_anchor
        "    NetplayVblankEpilogue ep{};"
        "    while (psx_rewind_is_open()) {"
        "    while (savestate_menu_open) {"
        "    while (runtime_settings_menu_open) {")
    string(FIND "${_frontend_text}" "${_anchor}" _position)
    if(_position EQUAL -1)
        message(FATAL_ERROR "Review minimized pause boundary: ${_anchor}")
    endif()
    string(REPLACE "${_anchor}" "${_anchor}\n    shinka_minimize_wait();" _frontend_text "${_frontend_text}")
endforeach()
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/src/minimize_pause.inc")
