#include "title_logo.h"
#include "psx_window_icon.h"
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <vector>
#define STBI_NO_STDIO
#include "../third_party/stb_image.h"

extern "C" unsigned char *shinka_title_load(int *width, int *height) {
    const char *setting = std::getenv("SHINKA_TITLE_LOGO");
    if (setting && setting[0] == '0') return nullptr;
    try {
        const std::filesystem::path icon(psx_window_icon_path(nullptr));
        if (icon.empty()) return nullptr;
        std::ifstream file(icon.parent_path() / "shinka-title.png", std::ios::binary | std::ios::ate);
        if (!file) return nullptr;
        const auto size = file.tellg();
        if (size <= 0 || size > 8 * 1024 * 1024) return nullptr;
        std::vector<unsigned char> bytes(static_cast<size_t>(size));
        file.seekg(0);
        if (!file.read(reinterpret_cast<char *>(bytes.data()), size)) return nullptr;
        int channels = 0;
        if (!stbi_info_from_memory(bytes.data(), static_cast<int>(bytes.size()), width, height, &channels)
            || *width < 1 || *height < 1 || *width > 4096 || *height > 4096
            || static_cast<int64_t>(*width) * *height > 4 * 1024 * 1024) return nullptr;
        return stbi_load_from_memory(bytes.data(), static_cast<int>(bytes.size()), width, height, &channels, 4);
    } catch (...) { return nullptr; }
}
extern "C" void shinka_title_free(unsigned char *pixels) { stbi_image_free(pixels); }
