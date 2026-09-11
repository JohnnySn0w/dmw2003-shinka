#ifndef SHINKA_MENU_WIDE_H
#define SHINKA_MENU_WIDE_H
#include <stdint.h>
int shinka_menu_root_active(void);
int shinka_menu_items_active(void);
int shinka_menu_wide_mode(unsigned mode);
int shinka_menu_wide_rect(uint32_t* words, int count, int offset_x, int offset_y,
    int left, int top, int right, int bottom, int margin);
#endif
