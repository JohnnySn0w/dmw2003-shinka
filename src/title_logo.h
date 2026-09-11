#ifndef SHINKA_TITLE_LOGO_H
#define SHINKA_TITLE_LOGO_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
void shinka_title_ready(int ready);
int shinka_title_command(const uint32_t *words, unsigned count, unsigned page,
                         int offset_x, int offset_y, int left, int top, int right, int bottom);
float shinka_title_opacity(void);
unsigned char *shinka_title_load(int *width, int *height);
void shinka_title_free(unsigned char *pixels);
#ifdef __cplusplus
}
#endif
#endif
