find_package(Python3 COMPONENTS Interpreter REQUIRED)
set(_generated "${CMAKE_CURRENT_BINARY_DIR}/shinka-runtime")
set(_reward "${CMAKE_CURRENT_SOURCE_DIR}/extracted/audit/STFGTREP.PRO")
if(NOT EXISTS "${_reward}")
    message(FATAL_ERROR "Extract STFGTREP.PRO from your disc with tools/build_windows.ps1")
endif()
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/tools/generate_menu_hooks.py" "${_reward}")
execute_process(COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tools/generate_menu_hooks.py"
    "${CMAKE_CURRENT_SOURCE_DIR}/output/recompiled" "${_generated}" "${_reward}"
    --manifest-output "${CMAKE_CURRENT_SOURCE_DIR}/output/exp-mod/manifest.toml"
    RESULT_VARIABLE _generated_result ERROR_VARIABLE _generated_error)
if(NOT _generated_result EQUAL 0)
    message(FATAL_ERROR "Review generated menu hooks: ${_generated_error}")
endif()
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/tools/generate_evolution_data.py"
    "${CMAKE_CURRENT_SOURCE_DIR}/tools/evolution_hints.py"
    "${CMAKE_CURRENT_SOURCE_DIR}/extracted/audit/STGDGLAB.PRO"
    "${CMAKE_CURRENT_SOURCE_DIR}/extracted/audit/SLES_039.36")
execute_process(COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tools/generate_evolution_data.py"
    "${CMAKE_CURRENT_SOURCE_DIR}/extracted/audit" "${_generated}/evolution_data.h"
    RESULT_VARIABLE _evolution_result ERROR_VARIABLE _evolution_error)
if(NOT _evolution_result EQUAL 0)
    message(FATAL_ERROR "Extract the supported STGDGLAB.PRO and review chart data: ${_evolution_error}")
endif()
get_target_property(_sources shinka SOURCES)
foreach(_shard 00 01 02 03 05)
    set(_original "${CMAKE_CURRENT_SOURCE_DIR}/output/recompiled/SLES_039.36_full_${_shard}.c")
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${_original}")
    if(NOT "${_original}" IN_LIST _sources)
        message(FATAL_ERROR "Generated source layout changed: ${_original}")
    endif()
    list(REMOVE_ITEM _sources "${_original}")
    list(APPEND _sources "${_generated}/journal_${_shard}.c")
endforeach()
set(_runtime "${PSXRECOMP_ROOT}/runtime/src/mod_runtime.cpp")
if(NOT "${_runtime}" IN_LIST _sources)
    message(FATAL_ERROR "Review pinned mod runtime target")
endif()
file(READ "${_runtime}" _runtime_code)
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/src/menu_settings_bridge.inc" _bridge)
set(_restore "void mod_runtime_on_savestate_loaded(void) {")
string(FIND "${_runtime_code}" "${_restore}" _restore_index)
if(_restore_index EQUAL -1)
    message(FATAL_ERROR "Review pinned savestate settings restore hook")
endif()
string(REPLACE "${_restore}" "extern \"C\" void shinka_rewards_refresh(void);\n${_restore}\n    shinka_rewards_refresh();" _runtime_code "${_runtime_code}")
file(CONFIGURE OUTPUT "${_generated}/mod_runtime.cpp" CONTENT "${_runtime_code}\n${_bridge}" @ONLY)
list(REMOVE_ITEM _sources "${_runtime}")
list(APPEND _sources "${_generated}/mod_runtime.cpp")
set_property(TARGET shinka PROPERTY SOURCES "${_sources}")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${_runtime}" "${CMAKE_CURRENT_SOURCE_DIR}/src/menu_settings_bridge.inc")
target_sources(shinka PRIVATE src/journal_menu.c src/menu_exp.c src/evolution_chart.c)
target_include_directories(shinka PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/output/recompiled" "${_generated}")
