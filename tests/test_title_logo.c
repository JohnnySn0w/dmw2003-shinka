#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include "title_logo.h"
static uint32_t mode = 0xe00;
static int started = 1;
static uint32_t module = 14;
int psx_mod_game_started(void) { return started; }
uint32_t psx_mod_read_word(uint32_t addr) {
    if (addr == 0x80055d28u) return module;
    assert(addr == 0x8004b3f8u); return mode;
}
static int command(uint32_t *w, unsigned page, int top) {
    return shinka_title_command(w,4,page,0,top,0,top,319,top+239);
}
int main(void) {
    uint32_t logo[] = {0x64808080,0x00170026,0x7c807040,0x00200020};
    uint32_t background[] = {0x64808080,0x00000000,0x7cc00000,0x00f00040};
    uint32_t menu[] = {0x64808080,0x009a004f,0x7e2be250,0x001000a4};
    uint32_t legal[] = {0x64808080,0x00c50048,0x7dea3bd0,0x0022002c};
    uint32_t frame[] = {0xe3000000};
    uint32_t fade[] = {0x32ffffff,0x007800a0,0x00ffffff,0xfff10000,0x00ffffff,0x01040000};
    uint32_t shadow[] = {0x66808080,0x00180019,0x7fe94800,0x00700028};
    assert(!command(logo,0x9b,0)); /* Missing asset / software fallback. */
    shinka_title_ready(1);
    assert(command(logo,0x9b,0));
    assert(shinka_title_opacity()==1.0f);
    assert(command(logo,0x9b,256)); /* Both native draw buffers. */
    assert(!command(background,0x8c,0));
    assert(!command(menu,0x1a,0));
    assert(!command(legal,0x1b,0));
    assert(command(shadow,0x1a,0));
    assert(!command(logo,0x9a,0));
    logo[2]^=1; assert(!command(logo,0x9b,0)); logo[2]^=1;
    assert(!command(logo,0x9b,240));
    assert(!shinka_title_command(logo,4,0x9b,0,0,0,0,639,479));
    assert(!shinka_title_command(logo,3,0x9b,0,0,0,0,319,239));
    for (mode=0;mode<=0x1000;mode++) {
        if(mode==0xe00 || mode==0xc00 || mode==0x2d7) continue;
        assert(!command(logo,0x9b,0));
        assert(shinka_title_opacity()==0.0f);
    }
    mode=0xe00; started=0; assert(!command(logo,0x9b,0)); started=1;
    mode=0xc00; assert(command(logo,0x9b,0));
    module=12; assert(!command(logo,0x9b,0)); assert(shinka_title_opacity()==0.0f);
    mode=0x1600; module=14; assert(command(logo,0x9b,0));
    mode=0xe00;
    shinka_title_command(fade,6,0,0,0,0,0,319,239);
    assert(shinka_title_opacity()==0.0f);
    shinka_title_command(frame,1,0,0,0,0,0,319,239);
    assert(shinka_title_opacity()==0.0f); /* No stale logo on an empty frame. */
    logo[0]=0x64404040; assert(command(logo,0x9b,0));
    assert(shinka_title_opacity()==0.5f);
    shinka_title_ready(0); assert(shinka_title_opacity()==0.0f);
    puts("title logo guards, draw buffers, fade and fallback passed");
    return 0;
}
