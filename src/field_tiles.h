#ifndef SHINKA_FIELD_TILES_H
#define SHINKA_FIELD_TILES_H
#include <stddef.h>
#include <stdint.h>
typedef struct { int16_t x,y,u,v,w,h; uint8_t layer; } ShinkaFieldPart;
typedef struct {
    uint16_t palette[256], pixels[128*128];
    unsigned width, height, count;
    ShinkaFieldPart parts[15];
} ShinkaFieldTile;
int shinka_field_decode(const uint8_t*, size_t, ShinkaFieldTile*);
void shinka_field_prepare(void);
void shinka_field_reset(void);
void shinka_field_gpu_source(uint32_t);
int shinka_field_texture_slot(void);
const ShinkaFieldTile* shinka_field_texture(unsigned, uint64_t*);
void shinka_field_graphics_ready(int);
uint32_t shinka_field_stat(unsigned);
#endif
