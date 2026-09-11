# The sample scheduler only needs SPUCNT, not a diagnostic snapshot of every
# voice, sweep envelope and reverb register. spu_read(DAA) returns the same
# register without advancing devices or changing the IRQ latch.
set(_source "${PSXRECOMP_ROOT}/runtime/src/interrupts.c")
file(READ "${_source}" _text)
set(_old "    spu_get_global_state(&state);")
string(REGEX MATCHALL "spu_get_global_state\\(&state\\)" _matches "${_text}")
list(LENGTH _matches _count)
if(NOT _count EQUAL 2)
    message(FATAL_ERROR "Review pinned SPU sample scheduling snapshot calls")
endif()
string(REGEX MATCHALL "state\\.[a-zA-Z0-9_]+" _members "${_text}")
list(REMOVE_DUPLICATES _members)
# The header include cpu_state.h also matches; ignore it explicitly.
list(REMOVE_ITEM _members "state.h")
if(NOT "${_members}" STREQUAL "state.ctrl")
    message(FATAL_ERROR "Review newly used SPU snapshot fields before optimizing")
endif()
# Retain the local struct declaration and .ctrl reads so the scheduler's
# branches stay identical. No other state members are used in either function.
string(REPLACE "${_old}" "    state.ctrl = (uint16_t)spu_read(0x1F801DAAu);" _text "${_text}")
file(CONFIGURE OUTPUT "${_generated}/interrupts.c" CONTENT "${_text}" @ONLY)
get_target_property(_sources shinka SOURCES)
if(NOT "${_source}" IN_LIST _sources)
    message(FATAL_ERROR "Review interrupts source target")
endif()
list(REMOVE_ITEM _sources "${_source}")
list(APPEND _sources "${_generated}/interrupts.c")
set_property(TARGET shinka PROPERTY SOURCES "${_sources}")

# Optimize across the small, frequently interacting device implementations.
# Generated game translation units stay outside this set: they are enormous
# and do not benefit from making every incremental link optimize the game.
# Cross-module inlining removes call boundaries in the word-paced DMA path
# without changing device deadlines, memory visibility, or interrupt ordering.
include("${CMAKE_CURRENT_SOURCE_DIR}/tools/cd_deadline.cmake")
get_target_property(_sources shinka SOURCES)
option(SHINKA_DEVICE_LTO "Link-time optimization for the Windows device scheduler" ON)
if(MSVC AND SHINKA_DEVICE_LTO)
    set(_lto_count 0)
    foreach(_runtime_source IN LISTS _sources)
        get_filename_component(_runtime_name "${_runtime_source}" NAME)
        if(_runtime_name MATCHES "^(psx_cycles|interrupts|dma|timers|cdrom|sio|memory|mdec|spu)\\.c$")
            math(EXPR _lto_count "${_lto_count} + 1")
            set_property(SOURCE "${_runtime_source}" APPEND PROPERTY COMPILE_OPTIONS "$<$<CONFIG:Release>:/GL>")
        endif()
    endforeach()
    if(NOT _lto_count EQUAL 9)
        message(FATAL_ERROR "Review pinned device LTO source set")
    endif()
    target_link_options(shinka PRIVATE "$<$<CONFIG:Release>:/LTCG>")
endif()
include("${CMAKE_CURRENT_SOURCE_DIR}/tools/pacing_perf.cmake")
