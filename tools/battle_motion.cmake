set(_motion_module "${CMAKE_CURRENT_SOURCE_DIR}/extracted/audit/FIGHTSTG.PRO")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/tools/generate_battle_motion_data.py" "${_motion_module}")
execute_process(COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tools/generate_battle_motion_data.py"
    "${_motion_module}" "${_generated}/battle_motion_data.h"
    RESULT_VARIABLE _motion_result ERROR_VARIABLE _motion_error)
if(NOT _motion_result EQUAL 0)
    message(FATAL_ERROR "Extract the supported FIGHTSTG.PRO: ${_motion_error}")
endif()

# Keep the cycle-aware load, load hazard tracking and PGXP path intact. Only
# replace the value returned at this one guarded model-timeline load site.
set(_source "${PSXRECOMP_ROOT}/runtime/src/dirty_ram_interp.c")
file(READ "${_source}" _text)
string(REGEX MATCHALL "case 0x23: \\{ /\\* LW \\*/" _matches "${_text}")
list(LENGTH _matches _count)
if(NOT _count EQUAL 1)
    message(FATAL_ERROR "Review pinned interpreter LW dispatch")
endif()
set(_old "        else\n            cpu->gpr[rt] = psx_cyc_load_word(cpu, addr, rt, 1u << rs);\n        psx_pgxp_load(cpu, insn, addr, cpu->gpr[rt]);")
string(FIND "${_text}" "${_old}" _site)
if(_site EQUAL -1)
    message(FATAL_ERROR "Review pinned interpreter cycle-aware LW path")
endif()
string(REPLACE "${_old}"
    "        else\n            cpu->gpr[rt] = psx_cyc_load_word(cpu, addr, rt, 1u << rs);\n        if (pc == 0x80083d30u && addr == 0x800a4464u && rt == 2u)\n            cpu->gpr[rt] = shinka_battle_motion_load(cpu->gpr[18], cpu->gpr[rt]);\n        psx_pgxp_load(cpu, insn, addr, cpu->gpr[rt]);"
    _text "${_text}")
file(CONFIGURE OUTPUT "${_generated}/dirty_ram_interp.c"
    CONTENT "#include <stdint.h>\nextern uint32_t shinka_battle_motion_load(uint32_t, uint32_t);\n${_text}" @ONLY)
get_target_property(_sources shinka SOURCES)
if(NOT "${_source}" IN_LIST _sources)
    message(FATAL_ERROR "Review interpreter source target before motion hook")
endif()
list(REMOVE_ITEM _sources "${_source}")
list(APPEND _sources "${_generated}/dirty_ram_interp.c")
set_property(TARGET shinka PROPERTY SOURCES "${_sources}")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${_source}")
target_sources(shinka PRIVATE src/battle_motion.c)
if(SHINKA_BUILD_TESTS)
    add_executable(shinka_battle_motion_test tests/test_battle_motion.c src/battle_motion.c)
    target_include_directories(shinka_battle_motion_test PRIVATE
        "${PSXRECOMP_ROOT}/runtime/include" "${_generated}")
    add_test(NAME battle_motion COMMAND shinka_battle_motion_test)
endif()
