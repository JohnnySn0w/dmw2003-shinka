# Keep narrow CRT and filesystem paths in the same UTF-8 encoding as SDL.
# This is per-process; it does not change the player's Windows locale.
if(WIN32)
    enable_language(RC)
endif()
function(shinka_windows_utf8 target)
    if(NOT WIN32)
        return()
    endif()
    set(manifest "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/../src/windows.manifest")
    set(resource "${CMAKE_CURRENT_BINARY_DIR}/${target}_utf8.rc")
    file(WRITE "${resource}" "1 24 \"${manifest}\"\n")
    target_sources(${target} PRIVATE "${resource}")
    if(MSVC)
        # The resource already includes the ordinary asInvoker UAC declaration.
        target_link_options(${target} PRIVATE /MANIFEST:NO)
    endif()
endfunction()
