#include "title_logo.h"
#include "psx_window_icon.h"
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <memory>
#define STBI_NO_STDIO
#include "../third_party/stb_image.h"

/* Match the logo's 220-pixel footprint in the native 320x240 title view.
 * Average premultiplied colors so transparent edges and shadows downsample
 * cleanly, then let the presentation texture use the menu's soft filtering. */
static void native_title_resolution(unsigned char *pixels, int *width, int *height) {
    if (*width <= 220) return;
    const int sw = *width, sh = *height, dw = 220;
    const int dh = std::max(1, (sh * dw + sw / 2) / sw);
    std::vector<unsigned char> reduced(static_cast<size_t>(dw) * dh * 4);
    for (int y = 0; y < dh; ++y) {
        const double y0 = double(y) * sh / dh, y1 = double(y + 1) * sh / dh;
        for (int x = 0; x < dw; ++x) {
            const double x0 = double(x) * sw / dw, x1 = double(x + 1) * sw / dw;
            double alpha = 0, rgb[3] = {};
            for (int sy = int(y0); sy < std::min(sh, int(std::ceil(y1))); ++sy) {
                const double wy = std::min(y1, double(sy + 1)) - std::max(y0, double(sy));
                for (int sx = int(x0); sx < std::min(sw, int(std::ceil(x1))); ++sx) {
                    const double weight = wy * (std::min(x1, double(sx + 1)) - std::max(x0, double(sx)));
                    const auto *p = pixels + (static_cast<size_t>(sy) * sw + sx) * 4;
                    const double a = weight * p[3];
                    alpha += a;
                    for (int c = 0; c < 3; ++c) rgb[c] += a * p[c];
                }
            }
            auto *p = reduced.data() + (static_cast<size_t>(y) * dw + x) * 4;
            for (int c = 0; c < 3; ++c)
                p[c] = alpha > 0 ? static_cast<unsigned char>(std::min(255.0, rgb[c] / alpha + .5)) : 0;
            p[3] = static_cast<unsigned char>(std::min(255.0, alpha / ((x1-x0)*(y1-y0)) + .5));
        }
    }
    std::memcpy(pixels, reduced.data(), reduced.size());
    *width = dw;
    *height = dh;
}

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
        std::unique_ptr<unsigned char, decltype(&stbi_image_free)> pixels(
            stbi_load_from_memory(bytes.data(), static_cast<int>(bytes.size()), width, height, &channels, 4),
            stbi_image_free);
        if (pixels) native_title_resolution(pixels.get(), width, height);
        return pixels.release();
    } catch (...) { return nullptr; }
}
extern "C" void shinka_title_free(unsigned char *pixels) { stbi_image_free(pixels); }
