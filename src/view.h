#ifndef SHINKA_VIEW_H
#define SHINKA_VIEW_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
int shinka_view_get(int option); /* 0: battle width, 1: battle zoom */
int shinka_view_set(int option, int value);
void shinka_view_tick(void);
int shinka_view_wide_active(void);
int shinka_view_zoom_percent(void);
void shinka_view_project(int64_t* xterm, int64_t* yterm);
void shinka_view_frontend(int wide);
#ifdef __cplusplus
}
#endif
#endif
