#include <stdint.h>
#include <zlib.h>

extern uint8_t *memory_get_ram_ptr(void);

/* The pinned runtime's static-overlay cache can accept an old module after
 * RAM replacement. Validate live bytes on every dispatch until write tracking
 * has a proven invalidation contract. Range order matches the emitter's CRC. */
int shinka_overlay_code_matches(const uint32_t *ranges, uint32_t count,
                                uint32_t expected_crc)
{
    const uint8_t *ram = memory_get_ram_ptr();
    const uint32_t ram_size = 2u * 1024u * 1024u;
    uLong crc = crc32(0L, Z_NULL, 0);
    if (!ram || !ranges || !count || count > 4096u) return 0;
    for (uint32_t i = 0; i < count; ++i) {
        uint32_t lo = ranges[i * 2u] & 0x1FFFFFFFu;
        uint32_t len = ranges[i * 2u + 1u];
        if (!len || lo >= ram_size || len > ram_size - lo) return 0;
        crc = crc32(crc, ram + lo, len);
    }
    return (uint32_t)crc == expected_crc;
}
