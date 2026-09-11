# Depth24 entry may read the previous GPU image back to CPU VRAM. Do that
# before applying a CPU upload, especially a full restored savestate image.
# Otherwise the entry readback overwrites the just-restored RGB888 pixels and
# borders with the previous scene. Patch only Shinka's generated renderer.
set(_movie_gl "${_generated}/gpu_gl_renderer.c")
file(READ "${_movie_gl}" _movie_gl_code)
foreach(_write "sw_vram_write(x,y,px);" "sw_vram_transfer_in(x,y,w,h,d);")
    set(_old "    ${_write}\n    depth24_upload_policy();")
    string(FIND "${_movie_gl_code}" "${_old}" _pos)
    if(_pos EQUAL -1)
        message(FATAL_ERROR "Review pinned movie upload/readback ordering")
    endif()
    string(REPLACE "${_old}" "    depth24_upload_policy();\n    ${_write}" _movie_gl_code "${_movie_gl_code}")
endforeach()
file(CONFIGURE OUTPUT "${_movie_gl}" CONTENT "${_movie_gl_code}" @ONLY)
