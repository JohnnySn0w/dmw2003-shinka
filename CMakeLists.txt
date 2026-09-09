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
    GAME_OVERLAY_STATIC_C "${SHINKA_OVERLAY_SOURCE}"
    GEN_MARKER "output/recompiled/SLES_039.36_dispatch.c"
    GEN_FULL_GLOB "output/recompiled/SLES_039.36_full_*.c"
)
add_custom_command(TARGET shinka POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_CURRENT_SOURCE_DIR}/game.toml" "$<TARGET_FILE_DIR:shinka>/game.toml")
