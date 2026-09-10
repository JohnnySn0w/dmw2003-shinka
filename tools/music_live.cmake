set(_music_spu "${PSXRECOMP_ROOT}/runtime/src/spu.c")
set(_music_generated "${CMAKE_CURRENT_BINARY_DIR}/shinka-runtime/spu.c")
execute_process(COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tools/generate_music_hooks.py"
    "${_music_spu}" "${_music_generated}"
    RESULT_VARIABLE _music_result ERROR_VARIABLE _music_error)
if(NOT _music_result EQUAL 0)
    message(FATAL_ERROR "Review music SPU hooks: ${_music_error}")
endif()
get_target_property(_music_sources shinka SOURCES)
if(NOT "${_music_spu}" IN_LIST _music_sources)
    message(FATAL_ERROR "Review pinned SPU target before replacing source")
endif()
list(REMOVE_ITEM _music_sources "${_music_spu}")
list(APPEND _music_sources "${_music_generated}")
set_property(TARGET shinka PROPERTY SOURCES "${_music_sources}")
target_sources(shinka PRIVATE src/music_live.cpp)
set(SHINKA_MUSIC_PACK "${CMAKE_CURRENT_SOURCE_DIR}/output/music-live/music-live.bin" CACHE FILEPATH "Locally generated live music instrument pack")
if(EXISTS "${SHINKA_MUSIC_PACK}")
    add_custom_command(TARGET shinka POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:shinka>/assets"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different "${SHINKA_MUSIC_PACK}"
            "$<TARGET_FILE_DIR:shinka>/assets/music-live.bin")
endif()
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${_music_spu}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/generate_music_hooks.py")
if(SHINKA_BUILD_TESTS)
    add_executable(shinka_music_live_test tests/test_music_live.cpp src/music_live.cpp)
    target_include_directories(shinka_music_live_test PRIVATE src)
    target_compile_features(shinka_music_live_test PRIVATE cxx_std_17)
    add_test(NAME music_live COMMAND shinka_music_live_test)
endif()
