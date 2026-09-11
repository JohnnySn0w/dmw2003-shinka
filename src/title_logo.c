#include "title_logo.h"
#include "mod_plugins.h"

static int available;
static float opacity;
static unsigned fade;

static int title_scene(void) {
    uint32_t mode;
    if (!psx_mod_game_started()) return 0;
    mode = psx_mod_read_word(0x8004b3f8u);
    /* The scene owner changes mode before the outgoing title has finished
     * drawing. Keep its final fade only while module 14 is still resident. */
    return (mode == 0xe00 || mode == 0x1600 || mode == 0xc00 || mode == 0x2d7)
        && psx_mod_read_word(0x80055d28u) == 14;
}

/* PAL title logo sprite identities, captured from the native title scene.
 * Background, menu choices and legal text use different CLUTs. Match the
 * complete rectangle/UV/page identity rather than deleting an entire palette. */
static const uint32_t sprites[][4] = {
    {0x00170026,0x7c807040,0x00200020,0x09b},
    {0x00370026,0x7c80e000,0x00180018,0x09b},
    {0x004f0026,0x7c80e018,0x00180018,0x09b},
    {0x0017004f,0x7c803000,0x00080010,0x09a},
    {0x001f0046,0x7c80a820,0x00180020,0x09b},
    {0x0037003e,0x7c80b800,0x00180028,0x09a},
    {0x004f003e,0x7c808800,0x00200020,0x09b},
    {0x00170066,0x7c80e048,0x00180018,0x09b},
    {0x002f0066,0x7c80c018,0x00200018,0x09b},
    {0x004f005e,0x7c80d000,0x00180028,0x09a},
    {0x001f007e,0x7c807838,0x00300020,0x09a},
    {0x004f0086,0x7c80c830,0x00200018,0x09b},
    {0x001f009e,0x7c800000,0x00500020,0x09b},
    {0x001f00be,0x7c800020,0x00500020,0x09b},
    {0x001f00de,0x7c800040,0x00500018,0x09b},
    {0x001700f6,0x7c805000,0x00180028,0x09b},
    {0x002f00f6,0x7c808058,0x00280020,0x09a},
    {0x005700f6,0x7c809e28,0x00180010,0x09a},
    {0x00570106,0x7c80706c,0x00100008,0x09a},
    {0x005c0027,0x7c406800,0x00200020,0x09b},
    {0x005c0047,0x7c409020,0x00180020,0x09b},
    {0x005c0067,0x7c409040,0x00180020,0x09b},
    {0x005c0087,0x7c402064,0x00180018,0x09b},
    {0x005c009f,0x7c407020,0x00200020,0x09b},
    {0x005c00bf,0x7c40a800,0x00180020,0x09b},
    {0x005c00df,0x7c40c848,0x00180018,0x09b},
    {0x005c00f7,0x7c403028,0x00180010,0x09a},
    {0x005c0107,0x7c40a838,0x00100010,0x09a},
    {0x006e0067,0x7c000064,0x00200018,0x09b},
    {0x006e007f,0x7c00a840,0x00200018,0x09b},
    {0x006d0097,0x7c00c000,0x00200018,0x09b},
    {0x006e00af,0x7c005028,0x00200020,0x09b},
    {0x00180019,0x7fe94800,0x00700028,0x01a},
    {0x00200041,0x7fe970f4,0x00680008,0x01a},
    {0x00180049,0x7fe900b0,0x00700010,0x01b},
    {0x00200059,0x7fe93048,0x00780008,0x01a},
    {0x00180061,0x7fe900b8,0x00800020,0x01a},
    {0x00200081,0x7fe90070,0x00780048,0x01a},
    {0x002000c9,0x7fe94828,0x00680020,0x01a},
    {0x001800e9,0x7fe900d8,0x00700020,0x01a},
    {0x00180109,0x7fe900c0,0x00600008,0x01b},
    {0x00180111,0x7fe938c8,0x00400008,0x01b},
};

void shinka_title_ready(int ready) { available = ready; opacity = 0; fade = 0; }

int shinka_title_command(const uint32_t *w, unsigned count, unsigned page,
                         int ox, int oy, int left, int top, int right, int bottom) {
    unsigned i, clut;
    if (!available || !count) return 0;
    /* Every native frame starts with its drawing-environment command. */
    if (w[0] >> 24 == 0xe3) { opacity = 0; fade = 0; return 0; }
    /* The original full-screen subtractive fade is four Gouraud triangles.
     * Observe its center intensity, retaining all original fade commands. */
    if (count == 6 && w[0] >> 24 == 0x32 && w[1] == 0x007800a0
        && w[3] == 0xfff10000 && w[5] == 0x01040000 && title_scene()) {
        fade = w[0] & 255u;
        return 0;
    }
    if (count != 4) return 0;
    clut = w[2] >> 16;
    if (clut == 0x7fe9) { if (w[0] >> 24 != 0x66) return 0; }
    else if (w[0] >> 24 != 0x64
        || (clut != 0x7c00 && clut != 0x7c40 && clut != 0x7c80)) return 0;
    if (!title_scene()) return 0;
    if (ox || left || right != 319 || (top != 0 && top != 256)
        || bottom != top + 239 || oy != top) return 0;
    for (i = 0; i < sizeof(sprites)/sizeof(sprites[0]); ++i) {
        if (w[1] == sprites[i][0] && w[2] == sprites[i][1]
            && w[3] == sprites[i][2] && page == sprites[i][3]) {
            if (clut != 0x7fe9) {
                unsigned shade = w[0] & 255u;
                float alpha = shade >= 128 ? 1.0f : shade / 128.0f;
                if (alpha > opacity) opacity = alpha;
            }
            return 1;
        }
    }
    return 0;
}

float shinka_title_opacity(void) {
    return available && title_scene() ? opacity * (255u-fade) / 255.0f : 0.0f;
}
