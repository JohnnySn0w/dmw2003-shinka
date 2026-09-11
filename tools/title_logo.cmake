# Extend only the generated Shinka renderer/GPU copies created by view.cmake.
set(_title_gpu "${_generated}/gpu.c")
set(_title_gl "${_generated}/gpu_gl_renderer.c")
file(READ "${_title_gpu}" _title_gpu_code)
set(_title_gp0 "    gp0_ring_record(gp0_cmd_buf, gp0_words_needed);")
string(FIND "${_title_gpu_code}" "${_title_gp0}" _pos)
if(_pos EQUAL -1)
    message(FATAL_ERROR "Review title logo command capture hook")
endif()
string(REPLACE "${_title_gp0}"
    "${_title_gp0}\n    if (shinka_title_command(gp0_cmd_buf, gp0_words_needed,\n            texpage_x | (texpage_y << 4) | (texpage_colors << 7),\n            draw_offset_x, draw_offset_y, draw_area_left, draw_area_top, draw_area_right, draw_area_bottom)) return;"
    _title_gpu_code "${_title_gpu_code}")
file(CONFIGURE OUTPUT "${_title_gpu}" CONTENT "#include \"title_logo.h\"\n${_title_gpu_code}" @ONLY)

file(READ "${_title_gl}" _title_gl_code)
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/src/title_logo_gl.inc" _title_helpers)
foreach(_anchor "static void gl_swap_with_osd(void) {" "            int ow = 0, oh = 0;" "void gl_renderer_shutdown(void) {")
    string(FIND "${_title_gl_code}" "${_anchor}" _pos)
    if(_pos EQUAL -1)
        message(FATAL_ERROR "Review title logo GL presentation/lifecycle hook")
    endif()
endforeach()
string(REPLACE "static void gl_swap_with_osd(void) {" "${_title_helpers}\nstatic void gl_swap_with_osd(void) {" _title_gl_code "${_title_gl_code}")
string(REPLACE "            int ow = 0, oh = 0;" "            int ow = 0, oh = 0;\n            shinka_title_gl_draw(ww, wh);" _title_gl_code "${_title_gl_code}")
string(REPLACE "void gl_renderer_shutdown(void) {" "void gl_renderer_shutdown(void) {\n    shinka_title_gl_reset();" _title_gl_code "${_title_gl_code}")
file(CONFIGURE OUTPUT "${_title_gl}" CONTENT "#include \"title_logo.h\"\nstatic void shinka_title_gl_reset(void);\n${_title_gl_code}" @ONLY)

target_sources(shinka PRIVATE src/title_logo.c src/title_logo_asset.cpp)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/src/title_logo_gl.inc")
add_custom_command(TARGET shinka POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:shinka>/assets"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_CURRENT_SOURCE_DIR}/assets/branding/shinka-title.png"
        "$<TARGET_FILE_DIR:shinka>/assets/shinka-title.png")
if(SHINKA_BUILD_TESTS)
    add_executable(shinka_title_logo_test tests/test_title_logo.c src/title_logo.c)
    target_include_directories(shinka_title_logo_test PRIVATE src "${PSXRECOMP_ROOT}/runtime/include")
    add_test(NAME title_logo COMMAND shinka_title_logo_test)
endif()
