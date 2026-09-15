#ifndef SHINKA_TRIGGER_SHORTCUTS_H
#define SHINKA_TRIGGER_SHORTCUTS_H
#include <stdint.h>

/* Host state only: never serialized with guest RAM. Require a release after
 * startup, state loads, focus loss or a disabled input context. */
struct ShinkaTriggerShortcuts {
    enum { view = 1u << 8, speed = 1u << 9, mask = view | speed };
    uint16_t armed = 0;
    bool turbo = false;
    void reset() { armed = 0; turbo = false; }
    unsigned poll(uint16_t down, bool enabled) {
        if (!enabled) { reset(); return 0; }
        unsigned pressed = down & armed & mask;
        armed = (uint16_t)(~down & mask);
        if (pressed & speed) turbo = !turbo;
        return pressed;
    }
};
#endif
