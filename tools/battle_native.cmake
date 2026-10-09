set(SHINKA_BATTLE_OVERLAY_SOURCE "" CACHE FILEPATH "Optional locally generated battle hotspot overlay")
set(SHINKA_MOVIE_OVERLAY_SOURCE "" CACHE FILEPATH "Optional locally generated movie transfer overlay")
if(SHINKA_BATTLE_OVERLAY_SOURCE OR SHINKA_MOVIE_OVERLAY_SOURCE)
    if(SHINKA_OVERLAY_SOURCE)
        set_property(SOURCE "${SHINKA_OVERLAY_SOURCE}" APPEND PROPERTY COMPILE_DEFINITIONS
            psx_overlay_dispatch=shinka_base_overlay_dispatch
            psx_overlay_static_get_stats=shinka_base_overlay_stats)
        set_property(SOURCE src/battle_native.c APPEND PROPERTY COMPILE_DEFINITIONS SHINKA_HAS_BASE_NATIVE=1)
    else()
        # Disc-only setup has no developer capture archive. Battle/movie units
        # are independently generated from the disc; other overlays fall back
        # to the existing interpreter until their code is available.
        target_sources(shinka PRIVATE src/overlay_guard.c)
        target_compile_definitions(shinka PRIVATE PSX_HAS_OVERLAY_DISPATCH=1)
    endif()
    foreach(_unit BATTLE MOVIE)
        if(SHINKA_${_unit}_OVERLAY_SOURCE)
            if(NOT EXISTS "${SHINKA_${_unit}_OVERLAY_SOURCE}")
                message(FATAL_ERROR "Missing ${_unit} overlay source")
            endif()
            string(TOLOWER "${_unit}" _name)
            set_property(SOURCE "${SHINKA_${_unit}_OVERLAY_SOURCE}" APPEND PROPERTY COMPILE_DEFINITIONS
                psx_overlay_dispatch=shinka_${_name}_overlay_dispatch
                psx_overlay_static_get_stats=shinka_${_name}_overlay_stats
                psx_overlay_static_code_matches=shinka_overlay_code_matches)
            set_property(SOURCE src/battle_native.c APPEND PROPERTY COMPILE_DEFINITIONS SHINKA_HAS_${_unit}_NATIVE=1)
            target_sources(shinka PRIVATE "${SHINKA_${_unit}_OVERLAY_SOURCE}")
        endif()
    endforeach()
    target_sources(shinka PRIVATE src/battle_native.c)
endif()
