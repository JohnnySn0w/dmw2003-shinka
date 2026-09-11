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
/* Opt-in dry voice-bus meter: after ADSR/pan, before reverb/main volume.
 * Roles are melody, bass, percussion, unclassified. Never alters audio. */
int shinka_music_meter_begin(unsigned frames);
int shinka_music_meter_active(void);
void shinka_music_meter_voice(int voice, int32_t left, int32_t right, int noise);
void shinka_music_meter_frame(void);
unsigned shinka_music_meter_frames(void);
double shinka_music_meter_rms(unsigned role);
double shinka_music_meter_peak(unsigned role);
#ifdef __cplusplus
}
#endif
#endif
