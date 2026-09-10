#ifndef SHINKA_DEV_NAV_H
#define SHINKA_DEV_NAV_H
#include <stdint.h>

typedef struct {
    uint32_t mode, queued, story, stage, x, y, facing, encounters, countdown;
    uint32_t quick_menu, quick_phase, quick_row;
} ShinkaNavState;
typedef struct { uint32_t level, hp, max_hp, mp, max_mp, strength; } ShinkaNavPartner;

void shinka_nav_state(ShinkaNavState* state);
void shinka_nav_partner(unsigned index, ShinkaNavPartner* partner);
/* NULL means success. All validation precedes the first write. */
const char* shinka_nav_warp(int stage, int x, int y, int facing, int expected_mode);
const char* shinka_nav_story(int value, int expected_mode);
const char* shinka_nav_flag(int flag, int value, int expected_mode);
const char* shinka_nav_encounters(int enabled, int expected_mode);
const char* shinka_nav_heal(int index, int expected_mode);
const char* shinka_nav_power(int index, int value, int expected_mode);
#endif
