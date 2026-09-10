cmake_minimum_required(VERSION 3.20)
project(dmw2003_shinka LANGUAGES C CXX)

set(PSXRECOMP_ROOT "" CACHE PATH "Local checkout of the pinned PSXRecomp framework")
if(NOT EXISTS "${PSXRECOMP_ROOT}/runtime/runtime.cmake")
    message(FATAL_ERROR "Set PSXRECOMP_ROOT to the framework documented in docs/groundwork-audit.md")
endif()
if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/output/recompiled/SLES_039.36_dispatch.c")
    message(FATAL_ERROR "Generate the game code first with tools/build_windows.ps1; this target must not silently build a setup-only executable.")
endif()
set(PSX_RECOMP_UI OFF CACHE BOOL "Baseline build has no setup launcher")
set(PSX_PGXP_VARIANT OFF CACHE BOOL "Build only the original rendering path")
set(PSX_REWIND OFF CACHE BOOL "Baseline does not depend on the rewind backend")
set(SHINKA_OVERLAY_SOURCE "" CACHE FILEPATH "Optional locally generated overlays_static.c")
if(SHINKA_OVERLAY_SOURCE AND NOT EXISTS "${SHINKA_OVERLAY_SOURCE}")
    message(FATAL_ERROR "SHINKA_OVERLAY_SOURCE does not exist")
endif()
include("${PSXRECOMP_ROOT}/runtime/runtime.cmake")
psxrecomp_add_game_runtime(shinka
    WINDOW_TITLE "Digimon World 2003 - Shinka baseline"
    EXE_NAME "dmw2003-shinka"
    DEFAULT_GAME_CONFIG_PATH "game.toml"
    MAX_PLAYERS 1
    APP_ICON "${CMAKE_CURRENT_SOURCE_DIR}/assets/shinka.ico"
    GAME_OVERLAY_STATIC_C "${SHINKA_OVERLAY_SOURCE}"
    GEN_MARKER "output/recompiled/SLES_039.36_dispatch.c"
    GEN_FULL_GLOB "output/recompiled/SLES_039.36_full_*.c"
)
# The no-launcher path commits mods before resolving --disc in the pinned
# frontend. Generate a local corrected copy; never edit the dependency checkout.
set(_frontend "${PSXRECOMP_ROOT}/runtime/src/main.cpp")
file(READ "${_frontend}" _frontend_text)
set(_commit_old "PSXRecompV4::mod_runtime_commit(resolved_disc, &mod_error)")
set(_commit_new "PSXRecompV4::mod_runtime_commit(disc_override_path ? std::filesystem::path(disc_override_path) : resolved_disc, &mod_error)")
string(FIND "${_frontend_text}" "${_commit_old}" _commit_position)
if(_commit_position EQUAL -1)
    message(FATAL_ERROR "Pinned frontend mod-commit site changed; review the CLI disc fix")
endif()
string(REPLACE "${_commit_old}" "${_commit_new}" _frontend_text "${_frontend_text}")
set(_main_entry "int main(int argc, char** argv) {")
string(FIND "${_frontend_text}" "${_main_entry}" _main_position)
if(_main_position EQUAL -1)
    message(FATAL_ERROR "Review the pinned frontend's journal registration site")
endif()
# Explicit registration survives MSVC's removal of unused C CRT constructors.
string(REPLACE "${_main_entry}"
    "extern \"C\" void shinka_register_journal(void);\nextern \"C\" void shinka_music_init(const char*);\n${_main_entry}\n    shinka_music_init(argv[0]);\n    shinka_register_journal();"
    _frontend_text "${_frontend_text}")
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/shinka-runtime")
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/src/view_frontend.inc" _view_frontend)
set(_view_refresh "static void refresh_widescreen_projection() {")
string(FIND "${_frontend_text}" "${_view_refresh}" _view_refresh_pos)
if(_view_refresh_pos EQUAL -1)
    message(FATAL_ERROR "Review pinned widescreen frontend hook")
endif()
string(REPLACE "${_view_refresh}" "${_view_frontend}\n${_view_refresh}\n    shinka_view_tick();"
    _frontend_text "${_frontend_text}")
set(_view_headless "    if (g_headless) {\n        ep.skip_pace = 1;\n        return ep;\n    }")
string(FIND "${_frontend_text}" "${_view_headless}" _view_headless_pos)
if(_view_headless_pos EQUAL -1)
    message(FATAL_ERROR "Review pinned headless camera update path")
endif()
string(REPLACE "${_view_headless}"
    "    if (g_headless) {\n        if (psx_mod_game_started()) g_ws_engaged = true;\n        refresh_widescreen_projection();\n        ep.skip_pace = 1;\n        return ep;\n    }"
    _frontend_text "${_frontend_text}")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/src/view_frontend.inc")
file(CONFIGURE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/shinka-runtime/main.cpp"
    CONTENT "${_frontend_text}" @ONLY)
get_target_property(_runtime_sources shinka SOURCES)
list(REMOVE_ITEM _runtime_sources "${_frontend}")
set_property(TARGET shinka PROPERTY SOURCES "${_runtime_sources}")
target_sources(shinka PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/shinka-runtime/main.cpp")
target_include_directories(shinka PRIVATE "${PSXRECOMP_ROOT}/runtime/src")
include("${CMAKE_CURRENT_SOURCE_DIR}/tools/journal_hooks.cmake")
include("${CMAKE_CURRENT_SOURCE_DIR}/tools/dev_nav.cmake")
if(SHINKA_OVERLAY_SOURCE)
    # Redirect only generated static-overlay calls; keep upstream sources intact.
    set_property(SOURCE "${SHINKA_OVERLAY_SOURCE}" APPEND PROPERTY
        COMPILE_DEFINITIONS psx_overlay_static_code_matches=shinka_overlay_code_matches)
    target_sources(shinka PRIVATE src/overlay_guard.c)
endif()
option(SHINKA_BUILD_TESTS "Build Shinka native regression tests" ON)
if(SHINKA_BUILD_TESTS)
    enable_testing()
    add_executable(shinka_overlay_guard_test tests/test_overlay_guard.c src/overlay_guard.c)
    target_link_libraries(shinka_overlay_guard_test PRIVATE ZLIB::ZLIB)
    add_test(NAME overlay_guard COMMAND shinka_overlay_guard_test)
    add_executable(shinka_journal_menu_test tests/test_journal_menu.c src/journal_menu.c)
    target_include_directories(shinka_journal_menu_test PRIVATE "${PSXRECOMP_ROOT}/runtime/include")
    add_test(NAME journal_menu COMMAND shinka_journal_menu_test)
    add_executable(shinka_menu_exp_test tests/test_menu_exp.c src/menu_exp.c)
    target_include_directories(shinka_menu_exp_test PRIVATE "${PSXRECOMP_ROOT}/runtime/include" "${CMAKE_CURRENT_BINARY_DIR}/shinka-runtime")
    add_test(NAME menu_exp COMMAND shinka_menu_exp_test)
    add_executable(shinka_evolution_chart_test tests/test_evolution_chart.c src/evolution_chart.c)
    target_include_directories(shinka_evolution_chart_test PRIVATE "${PSXRECOMP_ROOT}/runtime/include" "${CMAKE_CURRENT_BINARY_DIR}/shinka-runtime")
    add_test(NAME evolution_chart COMMAND shinka_evolution_chart_test)
    add_executable(shinka_encounters_test tests/test_encounters.c src/encounters.c)
    target_include_directories(shinka_encounters_test PRIVATE "${PSXRECOMP_ROOT}/runtime/include" "${CMAKE_CURRENT_BINARY_DIR}/shinka-runtime")
    add_test(NAME encounters COMMAND shinka_encounters_test)
    add_executable(shinka_map_travel_test tests/test_map_travel.c src/map_travel.c)
    target_include_directories(shinka_map_travel_test PRIVATE "${PSXRECOMP_ROOT}/runtime/include" "${CMAKE_CURRENT_BINARY_DIR}/shinka-runtime")
    add_test(NAME map_travel COMMAND shinka_map_travel_test)
    add_executable(shinka_dev_nav_test tests/test_dev_nav.c src/dev_nav.c)
    target_include_directories(shinka_dev_nav_test PRIVATE src)
    add_test(NAME dev_nav COMMAND shinka_dev_nav_test)
endif()
include("${CMAKE_CURRENT_SOURCE_DIR}/tools/music_live.cmake")
include("${CMAKE_CURRENT_SOURCE_DIR}/tools/view.cmake")
add_custom_command(TARGET shinka POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:shinka>/mods/packages/shinka.evolution-journal/0.1.0"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/evolution-journal/manifest.toml"
        "$<TARGET_FILE_DIR:shinka>/mods/packages/shinka.evolution-journal/0.1.0/manifest.toml"
    COMMAND ${CMAKE_COMMAND}
        "-DSOURCE=${CMAKE_CURRENT_SOURCE_DIR}/output/exp-mod"
        "-DDESTINATION=$<TARGET_FILE_DIR:shinka>/mods/packages/shinka.experience/0.1.0"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/tools/stage_exp.cmake"
    COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:shinka>/assets"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_CURRENT_SOURCE_DIR}/assets/shinka.png" "$<TARGET_FILE_DIR:shinka>/assets/psxrecomp.png"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_CURRENT_SOURCE_DIR}/game.toml" "$<TARGET_FILE_DIR:shinka>/game.toml")
