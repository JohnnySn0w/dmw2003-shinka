# Inject only authored resource metadata into the pinned conversion tools.
# The project-specific include runs before targets exist; attach at directory end.
include("${CMAKE_CURRENT_LIST_DIR}/windows_utf8.cmake")
cmake_language(DEFER CALL shinka_windows_utf8 psxrecomp-game)
cmake_language(DEFER CALL shinka_windows_utf8 psxrecomp-bios)
