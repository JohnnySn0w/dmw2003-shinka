#ifndef SHINKA_SETTINGS_BUTTONS_H
#define SHINKA_SETTINGS_BUTTONS_H
#include <stdint.h>
int shinka_settings_button_direction(unsigned uv, unsigned clut, unsigned page);
void shinka_settings_button_pixels(const uint16_t packed[36], const uint16_t palette[16],
    int right, uint16_t pixels[144]);
#endif
