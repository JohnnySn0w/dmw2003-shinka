#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mod_plugins.h"
#include "battle_motion_data.h"

#define R psx_mod_read_word

/* Diagnostic prototype. No guest writes or host-side animation phase: loading
 * a state, changing clips, or reusing an allocation cannot inherit a remainder. */
static int ram(uint32_t p, uint32_t size) {
    return !(p & 3) && p >= 0x80000000u && p <= 0x80200000u - size;
}
static int object(uint32_t p, uint32_t callback) {
    static const uint32_t methods[] = {
        0x80014274, 0x80014288, 0x80014298, 0x800142a4,
        0x800142ac, 0x800142c8, 0x800142e0, 0x800142f4
    };
    if (!ram(p, 0x50) || R(p + 0x48) != callback) return 0;
    for (unsigned i = 0; i < 8; ++i)
        if (R(p + 0x28 + i * 4) != methods[i]) return 0;
    return 1;
}
static uint32_t child(uint32_t p, uint32_t callback) {
    uint32_t count = R(p + 0x20), table = R(p + 0x24), found = 0;
    if (!count || count > 16 || !ram(table, count * 4)) return 0;
    for (unsigned i = 0; i < count; ++i) {
        uint32_t candidate = R(table + i * 4);
        if (object(candidate, callback)) {
            if (found) return 0; /* ambiguous ownership fails closed */
            found = candidate;
        }
    }
    return found;
}
static int combatant(uint32_t model) {
    uint32_t p = R(0x8005ccbc), table, control;
    if (!object(p, 0x80020b58)) return 0;
    p = child(p, 0x80087070); if (!p) return 0;
    p = child(p, 0x800a6c44); if (!p) return 0;
    p = child(p, 0x80087bb0); if (!p || !ram(p, 0x19c)) return 0;
    if (R(p + 0x20) != 8) return 0;
    table = R(p + 0x24);
    if (!ram(table, 32)) return 0;
    control = R(model + 0x64);
    /* The group's four action records and eight child slots are distinct. */
    if (control < p + 0x50 || control >= p + 0x180
        || (control - p - 0x50) % 0x4c || !R(control)) return 0;
    for (unsigned i = 0; i < 8; ++i)
        if (R(table + i * 4) == model) return 1;
    return 0;
}
static uint32_t half(uint32_t p) {
    return (R(p & ~3u) >> ((p & 2) * 8)) & 0xffffu;
}

uint32_t shinka_battle_motion_step(uint32_t model, uint32_t delta, unsigned factor) {
    uint32_t count, position, destination;
    if (factor != 2 || !delta || delta > 4) return delta;
    if (R(0x8004b3f8) != 0x600 || !ram(model, 0x2634)
        || !object(model, 0x80083e0c) || !combatant(model)) return delta;
    /* Check live instructions every time; an overlay reload invalidates this
     * site regardless of the address or any previous successful match. */
    for (unsigned i = 0; i < sizeof(battle_motion_code) / 4; ++i)
        if (R(0x80083a54 + i * 4) != battle_motion_code[i]) return delta;
    count = R(model + 0xa0); position = R(model + 0x80);
    if (R(model + 0x7c) || count < 2 || count > 1600 || position >= count - 1)
        return delta;
    destination = position + delta * factor;
    if (destination >= count) destination = count - 1;
    /* Let the original routine process the FIRST marker. Jumping straight to
     * the scaled endpoint could skip completion or a loop destination. Do not
     * wrap here: that would bypass the game's completion notification. */
    for (uint32_t next = position + 1; next <= destination; ++next) {
        uint32_t entry = half(model + 0xa4 + next * 2);
        if (entry == 0x8000 || entry == 0xffff) {
            if (entry == 0x8000 && half(model + 0xd24 + next * 2) >= count)
                return delta;
            destination = next;
            break;
        }
    }
    return destination - position;
}

uint32_t shinka_battle_motion_load(uint32_t model, uint32_t delta) {
    static int factor = -1, reported;
    uint32_t result;
    if (factor < 0) {
        const char* value = getenv("SHINKA_BATTLE_MOTION");
        factor = value && !strcmp(value, "2") ? 2 : 1;
    }
    if (factor == 1) return delta;
    result = shinka_battle_motion_step(model, delta, (unsigned)factor);
    if (!reported && result != delta) {
        fprintf(stderr, "[shinka] Experimental battle model motion: 2x, model=%08x step=%u->%u\n",
            model, delta, result);
        reported = 1;
    }
    return result;
}
