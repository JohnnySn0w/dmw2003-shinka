#ifndef SHINKA_MUSIC_LIVE_H
#define SHINKA_MUSIC_LIVE_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
int shinka_music_load(const char* path);
void shinka_music_init(const char* executable);
void shinka_music_reset(void);
void shinka_music_written(void);
int shinka_music_available(void);
void shinka_music_block(int palette);
void shinka_music_key_on(int voice, uint32_t address, const uint8_t* ram);
int16_t shinka_music_sample(int voice, uint32_t address, uint32_t pitch,
                          int16_t original, const uint8_t* ram, int noise);
const char* shinka_music_status(void);
unsigned shinka_music_matched_voices(void);
#ifdef __cplusplus
}
#endif
#endif
