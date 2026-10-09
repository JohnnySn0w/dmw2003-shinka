#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mod_plugins.h"
#include "battle_motion_data.h"

#define R psx_mod_read_word
extern int shinka_motion_get(int option);

/* Emulator-thread only. Fractions belong to a model/clip, never the global
 * clock. Clip setup and savestate hooks also clear these host-only records. */
typedef struct {
    uint32_t model, control, resource, clip, count, expected;
    unsigned percent, remainder;
} MotionPhase;
static MotionPhase phases[8];
void shinka_battle_motion_reset(void) { memset(phases, 0, sizeof(phases)); }
void shinka_battle_motion_restart(uint32_t model) {
    for (unsigned i = 0; i < 8; ++i)
        if (phases[i].model == model) memset(&phases[i], 0, sizeof(phases[i]));
}
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
        if (R(table + i * 4) == model) return (int)i + 1;
    return 0;
}
static uint32_t half(uint32_t p) {
    return (R(p & ~3u) >> ((p & 2) * 8)) & 0xffffu;
}

uint32_t shinka_battle_motion_step(uint32_t model, uint32_t delta, unsigned percent) {
    uint32_t count, position, destination, expected, control, resource, clip;
    MotionPhase* phase = NULL;
    unsigned remainder = 0, scaled;
    int slot;
    if ((percent != 125 && percent != 150 && percent != 200) || !delta || delta > 4)
        goto stock;
    if (R(0x8004b3f8) != 0x600 || !ram(model, 0x2634)
        || !object(model, 0x80083e0c)) goto stock;
    slot = combatant(model);
    if (!slot) goto stock;
    /* Check live instructions every time; an overlay reload invalidates this
     * site regardless of the address or any previous successful match. */
    for (unsigned i = 0; i < sizeof(battle_motion_code) / 4; ++i)
        if (R(0x80083a54 + i * 4) != battle_motion_code[i]) goto stock;
    count = R(model + 0xa0); position = R(model + 0x80);
    if (R(model + 0x7c) || count < 2 || count > 1600 || position >= count - 1)
        goto stock;
    control = R(model + 0x64); resource = R(model + 0x74); clip = R(model + 0x78);
    phase = &phases[slot - 1];
    if (phase->model == model && phase->control == control && phase->resource == resource
        && phase->clip == clip && phase->count == count && phase->expected == position
        && phase->percent == percent) remainder = phase->remainder;
    scaled = delta * (percent / 25) + remainder;
    destination = position + scaled / 4;
    if (destination >= count) destination = count - 1;
    expected = destination;
    /* Let the original routine process the FIRST marker. Jumping straight to
     * the scaled endpoint could skip completion or a loop destination. Do not
     * wrap here: that would bypass the game's completion notification. */
    for (uint32_t next = position + 1; next <= destination; ++next) {
        uint32_t entry = half(model + 0xa4 + next * 2);
        if (entry == 0x8000 || entry == 0xffff) {
            if (entry == 0x8000 && half(model + 0xd24 + next * 2) >= count)
                goto stock;
            destination = next;
            expected = entry == 0x8000 ? half(model + 0xd24 + next * 2) : next;
            break;
        }
    }
    *phase = (MotionPhase){model, control, resource, clip, count, expected, percent, scaled % 4};
    return destination - position;
stock:
    shinka_battle_motion_restart(model);
    return delta;
}

/* Use the game's per-actor default pose, rather than assuming that every
 * species' idle has a fixed clip number. All other poses use the action rate,
 * including attacks, reactions, entrances and victory motions. */
int shinka_battle_motion_category(uint32_t model) {
    uint32_t control, idle;
    if (!ram(model, 0x2634) || !object(model, 0x80083e0c)) return -1;
    control = R(model + 0x64);
    if (!ram(control, 0x4c)) return -1;
    idle = R(control + 0x18);
    if (idle == 0xffffffffu) return -1;
    return R(model + 0x78) == idle + 1 ? 0 : 1;
}

uint32_t shinka_battle_motion_load(uint32_t model, uint32_t delta) {
    static int override = -1, reported;
    int factor, category, idle, action;
    uint32_t result;
    if (override < 0) {
        const char* value = getenv("SHINKA_BATTLE_MOTION");
        override = value && !strcmp(value, "2") ? 200 : 0;
    }
    idle = override ? override : shinka_motion_get(0);
    action = override ? override : shinka_motion_get(1);
    if (idle == 100 && action == 100) { shinka_battle_motion_reset(); return delta; }
    category = shinka_battle_motion_category(model);
    if (category < 0) { shinka_battle_motion_restart(model); return delta; }
    factor = category ? action : idle;
    result = shinka_battle_motion_step(model, delta, (unsigned)factor);
    if (!reported && result != delta) {
        fprintf(stderr, "[shinka] Battle motion: idle=%d%% actions=%d%%, model=%08x step=%u->%u\n",
            idle, action, model, delta, result);
        reported = 1;
    }
    return result;
}

/* Deliberate script delays are separate from pose advancement. Scale the
 * positive operand once when a wait begins, never run the script twice or
 * change the shared clock. A camera already travelling keeps the stock wait.
 * This bounded ownership walk runs only at delay initialization. */
uint32_t shinka_battle_wait_load(uint32_t script, uint32_t operand, uint32_t ticks) {
    uint32_t pending[256], count = 1, root;
    int found = 0, camera = 0, rate = shinka_motion_get(2);
    if ((rate != 125 && rate != 150 && rate != 200) || !ticks || ticks > 32767)
        return ticks;
    root = R(0x8005ccbc);
    if (R(0x8004b3f8) != 0x600 || !ram(script, 0xb4)
        || !object(script, 0x8008c590) || R(script + 0x98) != 0
        || operand != R(script + 0x8c) || (operand & 1)
        || !ram(operand & ~3u, 4) || half(operand) != ticks
        || !object(root, 0x80020b58)) return ticks;
    for (unsigned i = 0; i < sizeof(battle_wait_code) / 4; ++i)
        if (R(0x8008c230 + i * 4) != battle_wait_code[i]) return ticks;
    pending[0] = root;
    for (unsigned i = 0; i < count; ++i) {
        uint32_t p = pending[i], children, table;
        if (!ram(p, 0x50) || !object(p, R(p + 0x48))) return ticks;
        if (p == script) found = 1;
        if (R(p + 0x48) == 0x80091df4) {
            if (!ram(p, 0x108) || R(p + 0xf0) != 4096) return ticks;
            camera = 1;
        }
        children = R(p + 0x20); table = R(p + 0x24);
        if (children > 64 || (children && !ram(table, children * 4))) return ticks;
        for (unsigned j = 0; j < children; ++j) {
            uint32_t candidate = R(table + j * 4);
            unsigned seen = 0;
            if (!candidate) continue;
            for (; seen < count && pending[seen] != candidate; ++seen) {}
            if (seen != count) continue;
            if (count == 256) return ticks;
            pending[count++] = candidate;
        }
    }
    if (!found || !camera) return ticks;
    return (ticks * 100u + (unsigned)rate - 1u) / (unsigned)rate;
}
