#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

extern uint8_t *memory_get_ram_ptr(void);

/* Keep immutable reference bytes after the first successful CRC validation.
 * EVERY later dispatch compares live RAM against those bytes. This is not a
 * cache of a previous match result and never relies on write generations.
 * Dispatch runs on the single guest execution thread. Cap retained allocations;
 * unusual/large functions and allocation failure keep the original CRC path. */
#define GUARD_SLOTS 1024u
#define GUARD_BYTES (1024u * 1024u)
typedef struct GuardReference {
    uint32_t crc, count;
    uint32_t *ranges; /* followed by concatenated reference code */
} GuardReference;
static GuardReference references[GUARD_SLOTS];
static uint32_t retained_bytes;

static int reference_cache_enabled(void) {
    static int enabled = -1;
    if (enabled < 0) {
        const char *e = getenv("SHINKA_GUARD_REFERENCE_CACHE");
        enabled = !e || e[0] != '0';
    }
    return enabled;
}

/* Validate live bytes on every dispatch. Range order matches the emitter's CRC. */
int shinka_overlay_code_matches(const uint32_t *ranges, uint32_t count,
                                uint32_t expected_crc)
{
    const uint8_t *ram = memory_get_ram_ptr();
    const uint32_t ram_size = 2u * 1024u * 1024u;
    if (!ram || !ranges || !count || count > 4096u) return 0;
    uint64_t bytes = 0;
    for (uint32_t i = 0; i < count; ++i) {
        uint32_t lo = ranges[i * 2u] & 0x1FFFFFFFu;
        uint32_t len = ranges[i * 2u + 1u];
        if (!len || lo >= ram_size || len > ram_size - lo) return 0;
        bytes += len;
    }
    GuardReference *empty = NULL;
    if (reference_cache_enabled()) {
        uint32_t slot = (expected_crc ^ ranges[0] ^ (count * 2654435761u)) & (GUARD_SLOTS-1u);
        for (uint32_t probe = 0; probe < GUARD_SLOTS; ++probe) {
            GuardReference *ref = &references[(slot+probe) & (GUARD_SLOTS-1u)];
            if (!ref->ranges) { empty = ref; break; }
            if (ref->crc != expected_crc || ref->count != count ||
                memcmp(ref->ranges, ranges, count*2u*sizeof(uint32_t))) continue;
            const uint8_t *code = (const uint8_t *)(ref->ranges + count*2u);
            for (uint32_t i = 0; i < count; ++i) {
                uint32_t lo = ranges[i*2u] & 0x1FFFFFFFu, len = ranges[i*2u+1u];
                if (memcmp(ram+lo, code, len)) return 0;
                code += len;
            }
            return 1;
        }
    }
    uLong crc = crc32(0L, Z_NULL, 0);
    for (uint32_t i = 0; i < count; ++i)
        crc = crc32(crc, ram+(ranges[i*2u] & 0x1FFFFFFFu), ranges[i*2u+1u]);
    if ((uint32_t)crc != expected_crc) return 0;
    uint64_t allocation = bytes + count*2u*sizeof(uint32_t);
    if (empty && allocation <= GUARD_BYTES-retained_bytes) {
        uint32_t *copy = (uint32_t *)malloc((size_t)allocation);
        if (copy) {
            memcpy(copy, ranges, count*2u*sizeof(uint32_t));
            uint8_t *code = (uint8_t *)(copy+count*2u);
            for (uint32_t i = 0; i < count; ++i) {
                uint32_t len = ranges[i*2u+1u];
                memcpy(code, ram+(ranges[i*2u] & 0x1FFFFFFFu), len);
                code += len;
            }
            empty->crc = expected_crc;
            empty->count = count;
            empty->ranges = copy;
            retained_bytes += (uint32_t)allocation;
        }
    }
    return 1;
}
