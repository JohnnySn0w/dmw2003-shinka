#include "settings_buttons.h"
extern int shinka_menu_settings_active(void);

int shinka_settings_button_direction(unsigned uv, unsigned clut, unsigned page) {
    /* Only the two extended-font chevrons in our Settings instruction. */
    if (clut != 0x3a17 || (page & 0x1ff) != 0x26
        || (uv != 0x1200 && uv != 0x1208) || !shinka_menu_settings_active()) return -1;
    return uv == 0x1208;
}

void shinka_settings_button_pixels(const uint16_t packed[36], const uint16_t palette[16],
    int right, uint16_t pixels[144]) {
    /* Resident English Cross sprite: 12x12, 4bpp. Preserve every outline,
     * shadow and face pixel. Only its blue X (indices 8/9) becomes face grey.
     * The arrow uses the native dark grey (index 2), not a new palette. */
    for (int y = 0; y < 12; ++y) for (int x = 0; x < 12; ++x) {
        unsigned index = (packed[y*3+x/4] >> ((x%4)*4)) & 15;
        if (index == 8 || index == 9) index = 1;
        int ax = right ? 11-x : x;
        int reach = y <= 5 ? y-3 : 8-y;
        if (reach >= 0 && ax >= 6-reach && ax <= 7) index = 2;
        pixels[y*12+x] = palette[index];
    }
}
