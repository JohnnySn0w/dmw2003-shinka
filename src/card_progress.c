#include "cpu_state.h"
#include "mod_plugins.h"

#define R psx_mod_read_word
#define W psx_mod_write_word

static int pointer(uint32_t p, unsigned size) {
    return p >= 0x80090000u && p <= 0x80200000u-size && !(p & 3);
}

/* Called at the resident read/write wrapper entry, before it changes s3.
 * STGMCARD's controller owns child 7 (the progress bar). Its native animation
 * advances 4096/duration per frame up to 95%, then finishes only after the
 * controller accepts the transfer/checksum result. Replace the estimate for
 * the save body; leave completion, errors, directory scans and headers alone.
 * No host state: restores and retries use the serialized completion count. */
void shinka_card_progress(CPUState* cpu) {
    uint32_t ra = cpu->gpr[31], owner = cpu->gpr[19];
    int writing = ra == 0x8008658cu;
    if ((!writing && ra != 0x80085ee8u) || cpu->gpr[6] != 0x26c4
        || !pointer(owner, 0x70) || R(owner+0x48) != 0x80087534
        || R(owner+0xc) != 1 || R(owner+0x20) != 10
        || R(owner+0x10) != (writing ? 53u : 71u)
        || R(0x80083c50) != 0x27bdfef0 || R(0x80083d1c) != 0xae42008c)
        return;
    uint32_t children = R(owner+0x24);
    if (!pointer(children, 40)) return;
    uint32_t bar = R(children+28);
    if (!pointer(bar, 0xd8) || R(bar+0x48) != 0x80083c50
        || R(bar+0x28) != 0x80014274 || R(bar+0xc) != 1
        || R(bar+0x10) != 1) return;
    uint32_t done = R(0x80048750) == (writing ? 4u : 3u) ? R(0x80048a50) : 0;
    if (done > 0x2700 || (done & 127)) return;
    /* The write header's two sectors have already completed before this
     * body call. Include them so entering the body cannot restart the bar. */
    W(bar+0x8c, (done + (writing ? 256u : 0u)) * 0xf33u
        / (0x2700u + (writing ? 256u : 0u)));
    /* One unit avoids the native zero-step initialization. Each wrapper
     * poll replaces this subpixel drift with the acknowledged byte count. */
    W(bar+0x78, 1);
}
