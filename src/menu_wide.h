#ifndef SHINKA_MENU_WIDE_H
#define SHINKA_MENU_WIDE_H
#include <stdint.h>
int shinka_menu_root_active(void);
int shinka_menu_items_active(void);
enum { SHINKA_STATUS_NONE, SHINKA_STATUS_ITEMS, SHINKA_STATUS_SORT, SHINKA_STATUS_TECHNIQUES,
    SHINKA_STATUS_CHARACTER, SHINKA_STATUS_DIGIVOLVE, SHINKA_STATUS_EQUIPMENT,
    SHINKA_STATUS_CHARACTER_SELECT, SHINKA_STATUS_CHARACTER_TECHNIQUES, SHINKA_STATUS_MAP };
int shinka_menu_status_layout(void);
int shinka_menu_map_pan(void);
int shinka_menu_wide_mode(unsigned mode);
int shinka_menu_wide_rect(uint32_t* words, int count, int offset_x, int offset_y,
    int left, int top, int right, int bottom, int margin);
#endif
