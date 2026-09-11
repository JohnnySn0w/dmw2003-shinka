#ifndef SHINKA_PACING_SLEEP_H
#define SHINKA_PACING_SLEEP_H
#include <stdint.h>

/* Sleep almost to the existing deadline, leaving 200 microseconds for the
 * final spin. The old millisecond rounding leaves up to two milliseconds.
 * Compare before subtraction: an overdue deadline must never underflow into
 * a huge sleep. Clamp to one frame just like the original pacer.
 */
static uint32_t shinka_pacing_sleep_us(uint64_t now, uint64_t deadline,
                                     uint64_t frequency, uint64_t period) {
    if (now >= deadline || frequency == 0) return 0;
    uint64_t remaining = deadline - now;
    if (remaining > period) remaining = period;
    /* Supported performance counters and frame periods fit this conversion.
     * Fail to spinning if supplied a corrupt period that could overflow. */
    if (remaining > UINT64_MAX / 1000000u) return 0;
    uint64_t us = remaining * 1000000u / frequency;
    if (us <= 200u) return 0;
    if (us > 50000u) us = 50000u;
    return (uint32_t)(us - 200u);
}
#endif
