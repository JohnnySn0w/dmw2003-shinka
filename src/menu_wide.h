#ifndef SHINKA_MENU_WIDE_H
#define SHINKA_MENU_WIDE_H
#include <stdint.h>
int shinka_menu_root_active(void);
int shinka_menu_items_active(void);
enum { SHINKA_STATUS_NONE, SHINKA_STATUS_ITEMS, SHINKA_STATUS_SORT, SHINKA_STATUS_TECHNIQUES,
    SHINKA_STATUS_CHARACTER, SHINKA_STATUS_DIGIVOLVE, SHINKA_STATUS_EQUIPMENT,
    SHINKA_STATUS_CHARACTER_SELECT, SHINKA_STATUS_CHARACTER_TECHNIQUES, SHINKA_STATUS_MAP,
    SHINKA_STATUS_FOLDERS, SHINKA_CARD_ALBUM, SHINKA_FOLDER_SELECT, SHINKA_FOLDER_EDIT,
    SHINKA_LAB, SHINKA_LAB_CHART, SHINKA_LAB_TECHNIQUES, SHINKA_FOLDER_EXPLAIN, SHINKA_LAB_LOAD,
    SHINKA_FOLDER_CARDS, SHINKA_FIELD_INN, SHINKA_FIELD_ENTRY };
int shinka_menu_status_layout(void);
int shinka_menu_map_pan(void);
enum { SHINKA_BOOT_NONE, SHINKA_BOOT_TITLE, SHINKA_BOOT_CARD };
int shinka_menu_boot_scene(unsigned mode);
int shinka_menu_wide_mode(unsigned mode);
int shinka_menu_wide_rect(uint32_t* words, int count, int offset_x, int offset_y,
    int left, int top, int right, int bottom, int margin);
int shinka_menu_backdrop_positions(const uint32_t* words, int count,
    int offset_x, int offset_y, int left, int top, int right, int bottom,
    int margin, int positions[8]);
void shinka_menu_animation_reset(void);
void shinka_menu_animation_tag(uint32_t source, const uint32_t* command,
    const uint32_t* rect, int pivot, int scale);
void shinka_menu_wide_quad(uint32_t* words, int count, uint32_t source,
    int offset_x, int offset_y, int left, int top, int right, int bottom, int margin);
#endif
