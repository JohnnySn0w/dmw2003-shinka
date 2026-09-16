#ifndef SHINKA_MENU_WIDE_H
#define SHINKA_MENU_WIDE_H
#include <stdint.h>
int shinka_menu_root_active(void);
int shinka_menu_items_active(void);
enum { SHINKA_STATUS_NONE, SHINKA_STATUS_ITEMS, SHINKA_STATUS_SORT, SHINKA_STATUS_TECHNIQUES,
    SHINKA_STATUS_CHARACTER, SHINKA_STATUS_DIGIVOLVE, SHINKA_STATUS_EQUIPMENT,
    SHINKA_STATUS_CHARACTER_SELECT, SHINKA_STATUS_CHARACTER_TECHNIQUES, SHINKA_STATUS_MAP,
    SHINKA_STATUS_FOLDERS, SHINKA_CARD_ALBUM, SHINKA_FOLDER_SELECT, SHINKA_FOLDER_EDIT,
    SHINKA_LAB, SHINKA_LAB_CHART, SHINKA_LAB_TECHNIQUES, SHINKA_FOLDER_EXPLAIN, SHINKA_LAB_LOAD };
int shinka_menu_status_layout(void);
int shinka_menu_map_pan(void);
int shinka_menu_wide_mode(unsigned mode);
int shinka_menu_wide_rect(uint32_t* words, int count, int offset_x, int offset_y,
    int left, int top, int right, int bottom, int margin);
void shinka_menu_animation_reset(void);
void shinka_menu_animation_tag(uint32_t source, const uint32_t* command,
    const uint32_t* rect, int pivot, int scale);
void shinka_menu_wide_quad(uint32_t* words, int count, uint32_t source,
    int offset_x, int offset_y, int left, int top, int right, int bottom, int margin);
#endif
