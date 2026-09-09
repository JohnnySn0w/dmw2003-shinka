# Runs after the framework stages its own catalog. Local disc-derived manifests
# are generated only after input verification and are never stored in Git.
if(EXISTS "${SOURCE}/manifest.toml")
    file(MAKE_DIRECTORY "${DESTINATION}")
    file(COPY "${SOURCE}/manifest.toml" DESTINATION "${DESTINATION}")
endif()
