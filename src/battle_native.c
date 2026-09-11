/* Optional locally generated battle/movie code. Each unit retains the baseline's
 * live-byte guard and has a process-local A/B control. */
#include "psx_runtime.h"
#include <stdio.h>
#include <stdlib.h>

extern int shinka_base_overlay_dispatch(CPUState *, uint32_t);
extern void shinka_base_overlay_stats(uint64_t *, uint64_t *, uint64_t *, uint64_t *);
#ifdef SHINKA_HAS_BATTLE_NATIVE
extern int shinka_battle_overlay_dispatch(CPUState *, uint32_t);
extern void shinka_battle_overlay_stats(uint64_t *, uint64_t *, uint64_t *, uint64_t *);

static int battle_native_enabled(void) {
    static int enabled = -1;
    if (enabled < 0) {
        const char *value = getenv("SHINKA_BATTLE_NATIVE");
        enabled = !value || value[0] != '0';
        fprintf(stdout, "Shinka battle native: %s (live-byte validation retained)\n",
                enabled ? "enabled" : "disabled");
    }
    return enabled;
}
#endif

#ifdef SHINKA_HAS_MOVIE_NATIVE
extern int shinka_movie_overlay_dispatch(CPUState *, uint32_t);
extern void shinka_movie_overlay_stats(uint64_t *, uint64_t *, uint64_t *, uint64_t *);
static int movie_native_enabled(void) {
    static int enabled = -1;
    if (enabled < 0) {
        const char *value = getenv("SHINKA_MOVIE_NATIVE");
        enabled = !value || value[0] != '0';
        fprintf(stdout, "Shinka movie native: %s (live-byte validation retained)\n",
                enabled ? "enabled" : "disabled");
    }
    return enabled;
}
#endif

int psx_overlay_dispatch(CPUState *cpu, uint32_t addr) {
#ifdef SHINKA_HAS_MOVIE_NATIVE
    if (movie_native_enabled() && shinka_movie_overlay_dispatch(cpu, addr)) return 1;
#endif
#ifdef SHINKA_HAS_BATTLE_NATIVE
    if (battle_native_enabled() && shinka_battle_overlay_dispatch(cpu, addr)) return 1;
#endif
    return shinka_base_overlay_dispatch(cpu, addr);
}

void psx_overlay_static_get_stats(uint64_t *checks, uint64_t *hits,
                                  uint64_t *variant_misses, uint64_t *address_misses) {
    uint64_t base[4], battle[4] = {0}, movie[4] = {0};
    shinka_base_overlay_stats(&base[0], &base[1], &base[2], &base[3]);
#ifdef SHINKA_HAS_BATTLE_NATIVE
    shinka_battle_overlay_stats(&battle[0], &battle[1], &battle[2], &battle[3]);
#endif
#ifdef SHINKA_HAS_MOVIE_NATIVE
    shinka_movie_overlay_stats(&movie[0], &movie[1], &movie[2], &movie[3]);
#endif
    if (checks) *checks = base[0]+battle[0]+movie[0];
    if (hits) *hits = base[1]+battle[1]+movie[1];
    if (variant_misses) *variant_misses = base[2]+battle[2]+movie[2];
    if (address_misses) *address_misses = base[3]+battle[3]+movie[3];
}
