#include <stdio.h>
#include <stdlib.h>
#include "view.h"
#define CHECK(c) do { if (!(c)) { fprintf(stderr,"line %d: %s\n",__LINE__,#c); exit(1); } } while (0)
static uint32_t mode;
static int started = 1, options[2], frontend;
int psx_mod_game_started(void) { return started; }
uint32_t psx_mod_read_word(uint32_t addr) { CHECK(addr == 0x8004b3f8); return mode; }
int shinka_view_get(int option) { return options[option]; }
void shinka_view_frontend(int wide) { frontend = wide; }
int main(void) {
    const uint32_t modes[] = {0, 0x202, 0x21d, 0x600, 0x700, 0xd00, 0xd01, 0x1000, 0x1400};
    for (unsigned m=0;m<sizeof(modes)/sizeof(*modes);++m) for(int w=0;w<2;++w) for(int z=0;z<3;++z) {
        int64_t x=12000000, y=-6000000;
        mode=modes[m];options[0]=w;options[1]=z;shinka_view_tick();
        int percent=mode==0x600 ? 100-10*z : 100;
        CHECK(frontend==(mode==0x600 && w));
        shinka_view_project(&x,&y);
        CHECK(x==120000*percent && y==-60000*percent);
    }
    mode=0x600;options[0]=1;options[1]=2;shinka_view_tick();
    mode=0x1000;int64_t x=65536,y=-65536;shinka_view_project(&x,&y);
    CHECK(x==65536 && y==-65536); /* immediate scene change before present */
    started=0;mode=0x600;shinka_view_tick();
    CHECK(!frontend && shinka_view_zoom_percent()==100);
    puts("Battle projection, scene isolation and independent camera settings passed.");
    return 0;
}
