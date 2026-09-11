# Extend a Shinka-owned copy, leaving the pinned dependency untouched.
set(_debug_original "${PSXRECOMP_ROOT}/runtime/src/debug_server.c")
file(READ "${_debug_original}" _debug_code)
set(_debug_anchor "static const CmdEntry s_commands[] = {")
string(REGEX MATCHALL "static const CmdEntry s_commands\\[\\] = \\{" _debug_matches "${_debug_code}")
list(LENGTH _debug_matches _debug_match_count)
if(NOT _debug_match_count EQUAL 1)
    message(FATAL_ERROR "Review pinned debug-server command table before adding Shinka navigation")
endif()
string(REPLACE "${_debug_anchor}"
    "#include \"dev_nav_server.inc\"\n${_debug_anchor}\n    { \"shinka_nav\", handle_shinka_nav },"
    _debug_code "${_debug_code}")
# Continuous GPU readback is a forensic feature, not a normal-play requirement.
# Preserve explicit opt-in and all one-shot captures without paying for a full
# 64-frame VRAM/display history at every eligible vblank.
set(_ring_old "const char *e = getenv(\"PSX_DISPLAY_RING\");\n        enabled = (!e || !*e || *e != '0') ? 1 : 0;")
string(FIND "${_debug_code}" "${_ring_old}" _ring_position)
if(_ring_position EQUAL -1)
    message(FATAL_ERROR "Review pinned display-history configuration before changing its default")
endif()
string(REPLACE "${_ring_old}"
    "const char *e = getenv(\"PSX_DISPLAY_RING\");\n        enabled = (e && *e && *e != '0') ? 1 : 0;"
    _debug_code "${_debug_code}")
string(REPLACE "Keep the forensic ring default-on, but"
    "Shinka makes the forensic ring opt-in (PSX_DISPLAY_RING=1);"
    _debug_code "${_debug_code}")
# Retrospective RAM history costs 128 MiB plus a record on every traced store.
# Leave range-filtered traces and write fingerprints independent of this opt-in.
set(_history_old [=[    /* Always-on catch-all wtrace ring (8 MB). Records EVERY RAM write
     * with lean fields (no register window). Sized for ~1 second of
     * coverage at typical Tomba write rates. */
    if (!s_wtrace_all) {
        s_wtrace_all = (WriteTraceAllEntry *)calloc(WRITE_TRACE_ALL_CAP,
                                                    sizeof(WriteTraceAllEntry));
    }]=])
set(_history_new [=[    /* Shinka: opt-in retrospective RAM history (128 MiB).
     * Targeted write traces and fingerprints remain available independently. */
    const char *write_history = getenv("PSX_WRITE_HISTORY");
    if (!s_wtrace_all && write_history && *write_history && *write_history != '0') {
        s_wtrace_all = (WriteTraceAllEntry *)calloc(WRITE_TRACE_ALL_CAP,
                                                    sizeof(WriteTraceAllEntry));
    }]=])
string(FIND "${_debug_code}" "${_history_old}" _history_position)
if(_history_position EQUAL -1)
    message(FATAL_ERROR "Review pinned RAM-history allocation before changing its default")
endif()
string(REPLACE "${_history_old}" "${_history_new}" _debug_code "${_debug_code}")
set(_history_stats_old [=[    send_fmt("{\"id\":%d,\"ok\":true,\"total\":%llu,\"capacity\":%d,"
             "\"oldest_seq\":%llu,\"newest_seq\":%llu}",
             id, (unsigned long long)total, WRITE_TRACE_ALL_CAP,]=])
set(_history_stats_new [=[    send_fmt("{\"id\":%d,\"ok\":true,\"total\":%llu,\"capacity\":%d,"
             "\"enabled\":%s,\"oldest_seq\":%llu,\"newest_seq\":%llu}",
             id, (unsigned long long)total, WRITE_TRACE_ALL_CAP,
             s_wtrace_all ? "true" : "false",]=])
string(FIND "${_debug_code}" "${_history_stats_old}" _history_stats_position)
if(_history_stats_position EQUAL -1)
    message(FATAL_ERROR "Review pinned RAM-history stats before adding allocation status")
endif()
string(REPLACE "${_history_stats_old}" "${_history_stats_new}" _debug_code "${_debug_code}")
string(REPLACE "wtrace_all not initialized"
    "wtrace_all unavailable; launch with PSX_WRITE_HISTORY=1 (requires 128 MiB)"
    _debug_code "${_debug_code}")
file(CONFIGURE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/shinka-runtime/debug_server.c"
    CONTENT "${_debug_code}" @ONLY)
get_target_property(_debug_sources shinka SOURCES)
if(NOT "${_debug_original}" IN_LIST _debug_sources)
    message(FATAL_ERROR "Review pinned debug-server build target")
endif()
list(REMOVE_ITEM _debug_sources "${_debug_original}")
set_property(TARGET shinka PROPERTY SOURCES "${_debug_sources}")
target_sources(shinka PRIVATE src/dev_nav.c "${CMAKE_CURRENT_BINARY_DIR}/shinka-runtime/debug_server.c")
target_include_directories(shinka PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${_debug_original}")
