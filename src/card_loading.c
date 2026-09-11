/* Batch the resident read wrapper's requests, retaining its first sector and
 * the library's asynchronous open/read/close, checksum and retry paths. */
#include <stdint.h>
#include <stdlib.h>

uint32_t shinka_card_read_size(uint32_t total, uint32_t done, int enabled) {
    uint32_t remaining;
    /* The original wrapper rounds its final read up to a whole sector. */
    if (!enabled || !done || !total || total > 128u * 1024u ||
        (done & 127u) || done >= total)
        return 128;
    remaining = ((total + 127u) & ~127u) - done;
    return remaining < 1024 ? remaining : 1024;
}

uint32_t shinka_card_read_chunk(uint32_t total, uint32_t done) {
    static int enabled = -1;
    if (enabled < 0) {
        const char *value = getenv("SHINKA_CARD_READ_BATCH");
        enabled = !value || value[0] != '0';
    }
    return shinka_card_read_size(total, done, enabled);
}

uint32_t shinka_card_read_completed(uint32_t total, uint32_t done, uint32_t requested) {
    /* Use the library's serialized request length, not today's batching
     * setting: an old savestate can resume with a single sector in flight. */
    if (total <= 128u * 1024u && !(done & 127u) &&
        done < total && requested >= 128 && requested <= 1024 &&
        !(requested & 127u) && requested <= ((total + 127u) & ~127u) - done)
        return requested;
    return 128;
}
