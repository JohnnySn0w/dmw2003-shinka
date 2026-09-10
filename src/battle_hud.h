#ifndef SHINKA_BATTLE_HUD_H
#define SHINKA_BATTLE_HUD_H
#include <stdint.h>
void shinka_battle_hud_command(uint32_t* words, int count, int offset_x, int offset_y,
    int left, int top, int right, int bottom, int margin);
int shinka_battle_hud_portrait(int left, int top, int right, int bottom, int margin);
int shinka_battle_hud_cursor(int sx, int sy, int dx, int dy, int w, int h, int margin);
#endif
