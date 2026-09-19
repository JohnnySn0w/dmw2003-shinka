#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "view.h"
#include "battle_hud.h"
#include "menu_wide.h"
#define CHECK(c) do { if (!(c)) { fprintf(stderr,"line %d: %s\n",__LINE__,#c); exit(1); } } while (0)
static uint32_t mode;
static uint32_t previous_mode, language = 2, destination = 5;
static uint32_t return_marker;
static int started = 1, options[3], frontend;
static int root_menu;
static int items_menu;
static int map_pan;
int shinka_menu_map_pan(void) { return map_pan; }
int shinka_menu_root_active(void) { return root_menu; }
int shinka_menu_items_active(void) { return items_menu; }
int shinka_menu_status_layout(void) { return items_menu; }
int psx_mod_game_started(void) { return started; }
uint32_t psx_mod_read_word(uint32_t addr) {
    if (addr == 0x8004b3f8) return mode;
    if (addr == 0x8004b400) return previous_mode;
    if (addr == 0x8004b404) return return_marker;
    if (addr == 0x8005cca8) return language;
    CHECK(addr == 0x8005ccf0); return destination;
}
int shinka_view_get(int option) { return options[option]; }
void shinka_view_frontend(int wide) { frontend = wide; }
static int floor_scale(int x, int scale) {
    /* Independent floating-point reference for the guest's arithmetic shift. */
    double value = (double)x * scale / 4096;
    int result = (int)value;
    return result > value ? result - 1 : result;
}
static void animation_tests(void) {
    /* Native ribbon, left party tile, right list tile, full-width footer.
     * Endpoints are captured native geometry and known 16:9 destinations. */
    static const struct { int x,y,w,h,pivot,wide_x,wide_w; unsigned uv; int root; } cases[] = {
        {34,13,32,25,320,169,32,0x26975fd4,1},
        {0,17,24,42,0,-53,24,0x2697b700,1},
        {168,40,40,22,320,221,40,0x26976300,1},
        {0,194,40,38,0,-53,53,0x7deab368,0},
        {108,120,32,32,124,55,32,0x7f6b2000,0},
        /* The same edge pivot also owns pieces translated to the OTHER side:
         * a stats panel opens from the right, and footer icons from the left. */
        {24,63,24,42,320,-29,24,0x2697b700,1},
        {168,40,40,22,0,221,40,0x26976300,1},
    };
    mode=0x1000;options[2]=1;previous_mode=0x21d;destination=4;
    shinka_view_tick();
    for(unsigned c=0;c<sizeof(cases)/sizeof(*cases);++c) for(int band=0;band<=256;band+=256)
    for(int scale=0;scale<=4096;scale+=128) {
        int x=cases[c].x,y=cases[c].y,w=cases[c].w,h=cases[c].h,p=cases[c].pivot;
        root_menu=cases[c].root;items_menu=root_menu ? 0 : SHINKA_STATUS_ITEMS;
        uint32_t rect[]={0x64808080,(uint16_t)x|((uint32_t)y<<16),cases[c].uv,w|((uint32_t)h<<16)};
        uint32_t quad[]={0x2c808080,0,rect[2],0,0x0006001f,0,0x00250000,0,0x0025001f};
        for(int i=0;i<4;++i) quad[1+i*2]=(uint16_t)(p+floor_scale(x+(i&1?w:0)-p,scale))
            | ((uint32_t)(y+(i&2?h:0))<<16);
        uint32_t original[9];memcpy(original,quad,sizeof(quad));
        shinka_menu_animation_tag(0x801d0004,quad,rect,p,scale);
        /* The owner can finish its close phase after building the packet. */
        root_menu=0;items_menu=0;
        shinka_menu_wide_quad(quad,9,0x1d0004,0,band,0,band,319,band+239,53);
        for(int i=0;i<4;++i) {
            int pivot=p==0 ? -53 : p==320 ? 373 : 71;
            int expected=pivot+floor_scale(cases[c].wide_x+(i&1?cases[c].wide_w:0)-pivot,scale);
            CHECK((int16_t)quad[1+i*2]==expected);
            CHECK((quad[1+i*2]>>16)==(original[1+i*2]>>16));
            CHECK(quad[2+i*2]==original[2+i*2]);
        }
        memcpy(quad,original,sizeof(quad));quad[2]^=1;
        shinka_menu_wide_quad(quad,9,0x1d0004,0,band,0,band,319,band+239,53);
        CHECK(quad[1]==original[1]); /* packet storage reused by another draw */
        shinka_menu_animation_reset();memcpy(quad,original,sizeof(quad));
        shinka_menu_wide_quad(quad,9,0x1d0004,0,band,0,band,319,band+239,53);
        CHECK(!memcmp(quad,original,sizeof(quad))); /* state-load invalidation */
    }
    /* Captured stat/divider/background strips must share every seam through
     * the entire open/close cycle, not just pass individual endpoint tests. */
    root_menu=0;
    for(int lab=0;lab<=1;++lab) for(int band=0;band<=256;band+=256)
    for(int margin=1;margin<=160;++margin) for(int step=0;step<=10;++step) {
        static const int status_x[]={80,120,160,184,220,256,292,328};
        static const int lab_x[]={84,104,136,168,208,236,264,292,320};
        const int* xs=lab ? lab_x : status_x;
        int strips=lab ? 8 : 7, scale=step*4096/10, last=0;
        mode=lab ? 0xd01 : 0x1000;items_menu=lab ? SHINKA_LAB_TECHNIQUES : SHINKA_STATUS_DIGIVOLVE;
        shinka_view_tick();
        for(int k=0;k<strips;++k) {
            int x=xs[k],w=xs[k+1]-x,y=lab ? 122 : 119;
            unsigned clut=lab ? 0x7cab : 0x7dea;
            uint32_t rect[]={0x64808080,x|((unsigned)y<<16),(clut<<16)|0xb490,w|(14u<<16)};
            uint32_t quad[]={0x2c808080,0,rect[2],0,0x6001f,0,0xd0000,0,0xd001f};
            for(int v=0;v<4;++v)quad[1+v*2]=(uint16_t)(320+floor_scale(x+(v&1?w:0)-320,scale))
                |((unsigned)(y+(v&2?14:0))<<16);
            shinka_menu_animation_tag(0x801d0004,quad,rect,320,scale);
            shinka_menu_wide_quad(quad,9,0x1d0004,0,band,0,band,319,band+239,margin);
            int dest=x+margin;
            CHECK((int16_t)quad[1]==320+margin+floor_scale(dest-320-margin,scale));
            if(k) CHECK((int16_t)quad[1]==last);
            last=(int16_t)quad[3];
        }
    }
    root_menu=0;items_menu=0;
    for(int band=0;band<=256;band+=256) for(int wide=0;wide<=1;++wide) {
        mode=0xf00;options[2]=wide;shinka_view_tick();
        uint32_t fade[]={0x2a555555,0,320,0x01000000,0x01000140};
        shinka_menu_wide_quad(fade,5,0,0,band,0,band,319,band+239,53);
        CHECK((int16_t)fade[1]==(wide ? -53 : 0));
        CHECK((int16_t)fade[2]==(wide ? 373 : 320));
        CHECK(fade[0]==0x2a555555 && fade[3]>>16==256);
        uint32_t partial[]={0x2a555555,0,319,0x01000000,0x0100013f};
        shinka_menu_wide_quad(partial,5,0,0,band,0,band,319,band+239,53);
        CHECK(!partial[1] && partial[2]==319);
    }
}
int main(void) {
    const uint32_t modes[] = {0, 0x1ff, 0x200, 0x202, 0x21d, 0x2ff, 0x300,
        0x600, 0x700, 0xa00, 0xa01, 0xc00, 0xc01, 0xd00, 0xd01, 0xe00, 0xf00, 0xf01, 0x1000, 0x1400};
    for (unsigned m=0;m<sizeof(modes)/sizeof(*modes);++m) for(int w=0;w<2;++w)
    for(int z=0;z<3;++z) for(int f=0;f<2;++f) {
        int64_t x=12000000, y=-6000000;
        mode=modes[m];options[0]=w;options[1]=z;options[2]=f;shinka_view_tick();
        int percent=mode==0x600 ? 100-10*z : 100;
        CHECK(frontend==((mode==0x600 && w) || (((mode>=0x200 && mode<0x300) || mode==0xa00 || mode==0xf00) && f)));
        shinka_view_project(&x,&y);
        CHECK(x==120000*percent && y==-60000*percent);
    }
    mode=0x600;options[0]=1;options[1]=2;shinka_view_tick();
    mode=0x1000;int64_t x=65536,y=-65536;shinka_view_project(&x,&y);
    CHECK(x==65536 && y==-65536); /* immediate scene change before present */
    started=0;mode=0x600;shinka_view_tick();
    CHECK(!frontend && shinka_view_zoom_percent()==100);
    mode=0x21d;options[2]=1;shinka_view_tick();
    CHECK(!frontend); /* field preview cannot affect boot */
    started=1;shinka_view_tick();CHECK(frontend);
    {
        uint32_t panel[]={0x64808080,0x001400CB,0x3E2059C4,0x001C0018};
        shinka_battle_hud_command(panel,4,0,0,0,0,319,239,53);
        CHECK(panel[1]==0x001400CB); /* battle anchors never move field sprites */
    }
    for(int band=0;band<=256;band+=256) for(int m=1;m<=160;++m) {
        mode=0xf00;options[2]=1;shinka_view_tick();
        int end=-m;
        for(int x=0;x<320;x+=32) {
            uint32_t panel[]={0x64808080,0x009c0000u|(unsigned)x,0x7eaa6400,0x00260020};
            int width=shinka_menu_wide_rect(panel,4,0,band,0,band,319,band+239,m);
            CHECK((int16_t)panel[1]==end && width>0);
            CHECK(panel[2]==0x7eaa6400 && panel[3]==0x00260020);
            end+=width;
        }
        CHECK(end==320+m); /* all ten strips meet without cracks */
        uint32_t a[]={0x64808080,0x00a00096,0x3a170000,0x000c0008};
        uint32_t b[]={0x64808080,0x00a000a2,0x3a170000,0x000c0008};
        CHECK(!shinka_menu_wide_rect(a,4,0,band,0,band,319,band+239,m));
        CHECK(!shinka_menu_wide_rect(b,4,0,band,0,band,319,band+239,m));
        CHECK((int16_t)b[1]-(int16_t)a[1]==12); /* description crosses column boundary intact */
        CHECK(a[3]==0x000c0008 && b[3]==0x000c0008); /* glyph size */
    }
    {
        uint32_t panel[]={0x64808080,0x009c0000,0x7eaa6400,0x00260020};
        mode=0x21d;shinka_view_tick();
        CHECK(!shinka_menu_wide_rect(panel,4,0,0,0,0,319,239,53));
        CHECK(panel[1]==0x009c0000);
        mode=0xf00;options[2]=0;shinka_view_tick();
        CHECK(!shinka_menu_wide_rect(panel,4,0,0,0,0,319,239,53));
        CHECK(panel[1]==0x009c0000);
        options[2]=1;shinka_view_tick();
        CHECK(!shinka_menu_wide_rect(panel,4,0,0,0,0,99,59,53));
        CHECK(panel[1]==0x009c0000); /* offscreen texture/portrait pass */
    }
    /* Every texture family repeats at native size. Across all scroll phases,
     * the two alternating columns cover the wide viewport without gaps or
     * overlap; packets/UVs remain untouched and redundant copies are skipped. */
    {
        const unsigned modes[]={0xa00,0xf00,0xf00,0x1000,0x400,0x1200,0xd01};
        const uint32_t textures[][3]={
            {0x7ca7b850,0x7ce65828,0x7ce75858},
            {0x7ca7b850,0x7ce65828,0x7ce75858},
            {0x7eea4230,0x7f2b3400,0x7eeb4260},
            {0x7da81060,0x7deb1090,0x7da93000},
            {0x3ae91a28,0x3b2b00a8,0x3b6b0078},
            {0x3f6b0060,0x3fab0030,0x3feb0000},
            {0x7d28ba30,0x7d68bb00,0x7d2a3814}};
        for(int scene=0;scene<7;++scene) for(int band=0;band<=256;band+=256)
        for(int margin=1;margin<=160;++margin) for(int phase=0;phase<96;++phase) {
            mode=modes[scene];items_menu=scene>=4 ? SHINKA_LAB : SHINKA_STATUS_ITEMS;
            options[2]=1;shinka_view_tick();
            int coverage[640]={0};
            for(int col=0;col<2;++col) for(int layer=0;layer<3;++layer) {
                int x=(phase+48*col)%96, positions[8];
                uint32_t tile[]={0x64808080,0x00200000u|(unsigned)x,textures[scene][layer],0x00300030};
                uint32_t original[4];memcpy(original,tile,sizeof tile);
                CHECK(!shinka_menu_wide_rect(tile,4,0,band,0,band,319,band+239,margin));
                int n=shinka_menu_backdrop_positions(tile,4,0,band,0,band,319,band+239,margin,positions);
                CHECK(n>0 && n<=8 && !memcmp(tile,original,sizeof tile));
                for(int i=0;i<n;++i) {
                    CHECK((positions[i]-x)%96==0);
                    CHECK(positions[i]+48>-margin && positions[i]<320+margin);
                    if(i) CHECK(positions[i]-positions[i-1]==96);
                    if(!layer) for(int px=positions[i];px<positions[i]+48;++px)
                        if(px>=-margin && px<320+margin) ++coverage[px+margin];
                }
                tile[1]+=96;
                CHECK(shinka_menu_backdrop_positions(tile,4,0,band,0,band,319,band+239,margin,positions)==-1);
            }
            for(int px=0;px<320+2*margin;++px) CHECK(coverage[px]==1);
        }
        int positions[8];
        mode=0x1000;items_menu=SHINKA_STATUS_ITEMS;
        for(int bad=0;bad<10;++bad) {
            uint32_t tile[]={0x64808080,0x00200010,0x7da81060,0x00300030};
            options[2]=bad==0 ? 0 : 1;shinka_view_tick();
            if(bad==1) tile[2]^=1;
            if(bad==2) tile[3]^=1;
            if(bad==3) tile[0]=0x66808080;
            if(bad==7) tile[1]=0x002001c1; /* beyond the native backdrop grid */
            CHECK(!shinka_menu_backdrop_positions(tile,bad==8?3:4,bad==9?1:0,0,0,0,bad==4?255:319,239,
                bad==5?0:bad==6?161:53,positions));
        }
        options[2]=1;shinka_view_tick();
    }
    root_menu=0;items_menu=0;
    for(int fullscreen=0;fullscreen<2;++fullscreen) {
        mode=fullscreen ? 0x1000 : 0x21d;root_menu=1;options[2]=1;shinka_view_tick();
        CHECK(frontend);
        uint32_t cursor[]={0x64808080,0x003100b0,0x3a170000,0x000c0008};
        uint32_t field[]={0x64808080,0x003100b0,0x3c400000,0x00800080};
        shinka_menu_wide_rect(cursor,4,0,0,0,0,319,239,53);
        shinka_menu_wide_rect(field,4,0,0,0,0,319,239,53);
        CHECK(cursor[1]==0x003100e5 && cursor[3]==0x000c0008);
        CHECK(field[1]==0x003100b0 && field[3]==0x00800080);
        uint32_t button[]={0x64808080,0x00130099,0x38174ab4,0x000c000c};
        shinka_menu_wide_rect(button,4,0,0,0,0,319,239,53);
        CHECK(button[1]==0x001300ce && button[2]==0x38174ab4); /* native green triangle */
        for(int band=0;band<=256;band+=256) for(int margin=1;margin<=160;++margin) {
            /* Visible 4:3 edge is x=116; preserve the cap, shorten the body. */
            int end=116+margin;
            for(int tile=0;tile<9;++tile) {
                int x=34+32*tile;
                uint32_t ribbon[]={0x64808080,0x000d0000u|(unsigned)x,
                    tile ? 0x26978d20u : 0x26975fd4u,0x00190020};
                int width=shinka_menu_wide_rect(ribbon,4,0,band,0,band,319,band+239,margin);
                CHECK(width>0 && (tile || width==32));
                CHECK((int16_t)ribbon[1]==end && ribbon[3]==0x00190020);
                end+=width;
            }
            CHECK(end-(168+margin)==154); /* original right edge relative to menu */
        }
        root_menu=0;shinka_view_tick();
        CHECK(frontend==!fullscreen); /* unsupported children immediately use 4:3 */
    }
    /* Actual field -> Items loader interval: the destination exists before its
     * tasks. The GPU predicate must work even before another frontend tick. */
    started=1;mode=0x21d;root_menu=1;options[2]=1;shinka_view_tick();
    root_menu=0;mode=0x1000;previous_mode=0x21d;destination=0;
    CHECK(shinka_view_wide_requested());
    for(int call=0;call<1000;++call) { shinka_view_tick();CHECK(frontend); }
    {
        uint32_t tile[]={0x64808080,0x00200000,0x7da81060,0x00300030};
        uint32_t panel[]={0x64808080,0x00c20000,0x7deab368,0x00260028};
        CHECK(!shinka_menu_wide_rect(tile,4,0,0,0,0,319,239,53));
        int positions[8];
        CHECK(shinka_menu_backdrop_positions(tile,4,0,0,0,0,319,239,53,positions)>0);
        CHECK((int16_t)tile[1]==0); /* closing backdrop retains original motion */
        CHECK(!shinka_menu_wide_rect(panel,4,0,0,0,0,319,239,53));
        CHECK(panel[1]==0x00c20000); /* pending presentation isn't layout admission */
    }
    options[2]=0;CHECK(!shinka_view_wide_requested());shinka_view_tick();CHECK(!frontend);
    options[2]=1;
    for(unsigned row=0;row<8;++row) {
        destination=row;shinka_view_tick();CHECK(frontend==(row<=6));
    }
    destination=0;language=3;shinka_view_tick();CHECK(!frontend);language=2;
    previous_mode=0x600;shinka_view_tick();CHECK(!frontend); /* stale row after a state load */
    for(int card=0;card<2;++card) {
        previous_mode=card ? 0x1200 : 0xd01;destination=card ? 5 : 6;
        shinka_view_tick();CHECK(frontend); /* return from card overlay / portable lab */
        destination=7;shinka_view_tick();CHECK(!frontend);
    }
    destination=0;
    previous_mode=0xd01;destination=4;return_marker=0x53484c42;
    shinka_view_tick();CHECK(frontend);
    return_marker=0;shinka_view_tick();CHECK(!frontend);
    destination=0;
    previous_mode=0x21d;started=0;shinka_view_tick();CHECK(!frontend);started=1;
    mode=0xd00;CHECK(!shinka_view_wide_requested()); /* unrelated overlay */
    mode=0x1000;previous_mode=0;destination=2;
    for(int field=0;field<2;++field) for(int band=0;band<=256;band+=256)
    for(int margin=1;margin<=160;++margin) for(unsigned palette=0x3c17;palette<=0x3fd7;palette+=64) {
        mode=field ? 0x21d : 0x1000;previous_mode=0x21d;destination=0;shinka_view_tick();
        int end=-margin;
        for(int col=0;col<5;++col) {
            uint32_t wipe[]={0x66808080,0xfff40000u|(unsigned)(col*64),(palette<<16)|0x5f40,0x00400040};
            int width=shinka_menu_wide_rect(wipe,4,0,band,0,band,319,band+239,margin);
            CHECK(width>0 && (int16_t)wipe[1]==end);
            CHECK(wipe[2]==((palette<<16)|0x5f40) && wipe[3]==0x00400040);
            end+=width;
        }
        CHECK(end==320+margin);
    }
    for(int scenario=0;scenario<5;++scenario) {
        uint32_t wipe[]={0x66808080,0x003400c0,0x3dd75f40,0x00400040};
        mode=scenario==0 ? 0xd00 : 0x1000;destination=scenario==1 ? 7 : 0;
        if(scenario==2) wipe[2]^=1;
        if(scenario==3) wipe[2]=0x3dd65f40;
        options[2]=scenario==4 ? 0 : 1;shinka_view_tick();
        CHECK(!shinka_menu_wide_rect(wipe,4,0,0,0,0,319,239,53));
        CHECK(wipe[1]==0x003400c0);
    }
    options[2]=1;previous_mode=0;destination=2;
    root_menu=1;shinka_view_tick();CHECK(frontend);
    mode=0x1000;items_menu=1;options[2]=1;shinka_view_tick();CHECK(frontend);
    root_menu=0;items_menu=1;shinka_view_tick();CHECK(frontend);
    /* Captured Choose Digimon packets use 0x2697, unlike the 0x7dea
     * character-detail header. The old column split tore these nine strips. */
    for(int band=0;band<=256;band+=256) for(int margin=1;margin<=160;++margin) {
        items_menu=SHINKA_STATUS_CHARACTER_SELECT;options[2]=1;shinka_view_tick();
        int end=144+margin;
        for(int tile=0;tile<9;++tile) {
            uint32_t strip[]={0x64808080,0x000d0000u|(unsigned)(34+tile*32),
                tile ? 0x26978d20u : 0x26975fd4u,0x00190020};
            int span=shinka_menu_wide_rect(strip,4,0,band,0,band,319,band+239,margin);
            CHECK((int16_t)strip[1]==end && span>0 && (tile || span==32));
            CHECK(strip[2]==(tile ? 0x26978d20u : 0x26975fd4u) && strip[3]==0x00190020);
            end+=span;
            options[2]=0;shinka_view_tick();
            strip[1]=0x000d0000u|(unsigned)(34+tile*32);
            CHECK(!shinka_menu_wide_rect(strip,4,0,band,0,band,319,band+239,margin));
            CHECK(strip[1]==(0x000d0000u|(unsigned)(34+tile*32)));
            options[2]=1;shinka_view_tick();
        }
        CHECK(end==322+margin);
        uint32_t title[]={0x64808080,0x00130099,0x3a1715c0,0x000c0008};
        uint32_t portrait[]={0x64808080,0x00130067,0x26975f80,0x002c002c};
        shinka_menu_wide_rect(title,4,0,band,0,band,319,band+239,margin);
        shinka_menu_wide_rect(portrait,4,0,band,0,band,319,band+239,margin);
        CHECK((int16_t)title[1]==177+margin && (int16_t)portrait[1]==103-margin);
    }
    items_menu=SHINKA_STATUS_ITEMS;shinka_view_tick();
    for(int band=0;band<=256;band+=256) for(int margin=1;margin<=160;++margin) {
        const unsigned backgrounds[]={0x7da81060,0x7deb1090,0x7da93000};
        int ribbon_end=144+margin;
        for(int tile=0;tile<9;++tile) {
            uint32_t ribbon[]={0x64808080,0x000d0000u|(unsigned)(34+tile*32),
                tile ? 0x26978d20u : 0x26975fd4u,0x00190020};
            int width=shinka_menu_wide_rect(ribbon,4,0,band,0,band,319,band+239,margin);
            CHECK(width>0 && (tile || width==32));
            CHECK((int16_t)ribbon[1]==ribbon_end && ribbon[3]==0x00190020);
            ribbon_end+=width;
        }
        CHECK(ribbon_end==322+margin); /* 24px visible overhang at the menu's left */
        for(int layer=0;layer<3;++layer) {
            for(int x=0;x<384;x+=48) {
                uint32_t tile[]={0x64808080,0x00200000u|(unsigned)x,backgrounds[layer],0x00300030};
                int width=shinka_menu_wide_rect(tile,4,0,band,0,band,319,band+239,margin);
                CHECK((int16_t)tile[1]==x && width==0);
                CHECK(tile[2]==backgrounds[layer] && tile[3]==0x00300030);
            }
        }
        /* Captured anchors: list columns, full description, page numerator,
         * separator/denominator, summary counts, tab, ribbon, portrait frame. */
        const int positions[][3]={{57,37,-1},{188,37,1},{190,203,-1},
            {149,156,0},{160,156,0},{172,156,0},{218,175,0},{290,175,1},
            {20,20,-1},{153,19,1},{116,19,-1},{253,152,1}};
        for(unsigned i=0;i<sizeof(positions)/sizeof(*positions);++i) {
            uint32_t glyph[]={0x64808080,((unsigned)positions[i][1]<<16)|(unsigned)positions[i][0],
                i==10 ? 0x7f28c14cu : i==11 ? 0x7faa0098u : 0x3a170000u,0x000c0008};
            CHECK(!shinka_menu_wide_rect(glyph,4,0,band,0,band,319,band+239,margin));
            CHECK((int16_t)glyph[1]==positions[i][0]+positions[i][2]*margin+(i==9 ? 24 : 0));
            CHECK(glyph[3]==0x000c0008);
        }
        uint32_t panel[]={0x64808080,0x00c20000,0x7deab368,0x00260028};
        CHECK(shinka_menu_wide_rect(panel,4,0,band,0,band,319,band+239,margin)>0);
        CHECK((int16_t)panel[1]==-margin && panel[3]==0x00260028);
        for(unsigned palette=0x3057;palette<=0x3157;palette+=64) {
            uint32_t advance[]={0x64808080,0x00d60123,(palette<<16)|0x3c54,0x000c000c};
            CHECK(!shinka_menu_wide_rect(advance,4,0,band,0,band,319,band+239,margin));
            CHECK((int16_t)advance[1]+12==303*(320+2*margin)/320-margin);
            CHECK(advance[3]==0x000c000c);
        }
    }
    for(int kind=SHINKA_STATUS_SORT;kind<=SHINKA_STATUS_TECHNIQUES;++kind)
    for(int band=0;band<=256;band+=256) for(int margin=1;margin<=160;++margin) {
        mode=0x1000;root_menu=0;items_menu=kind;options[2]=1;shinka_view_tick();CHECK(frontend);
        uint32_t title[]={0x64808080,0x00130099,0x3a170000,0x000c0008};
        shinka_menu_wide_rect(title,4,0,band,0,band,319,band+239,margin);
        CHECK((int16_t)title[1]==153+margin+24);
        uint32_t card[]={0x64808080,0x00130074,0x7f28c14c,0x000c0008};
        shinka_menu_wide_rect(card,4,0,band,0,band,319,band+239,margin);
        CHECK((int16_t)card[1]==116-margin);
        if(kind==SHINKA_STATUS_TECHNIQUES) {
            /* The list tab starts before x=160; it must stay with its text,
             * panel and cursor rather than split around the old midpoint. */
            const int xs[]={148,157,164,166,196,316};
            for(unsigned i=0;i<sizeof(xs)/sizeof(*xs);++i) {
                uint32_t list[]={0x64808080,0x00310000u|(unsigned)xs[i],
                    i ? 0x3a170000u : 0x7dea8060u,0x000c0008};
                CHECK(!shinka_menu_wide_rect(list,4,0,band,0,band,319,band+239,margin));
                CHECK((int16_t)list[1]==xs[i]+margin);
            }
            uint32_t cost[]={0x64808080,0x00d40126,0x3a171590,0x000c0008};
            uint32_t prose[]={0x64808080,0x00c60126,0x3a171590,0x000c0008};
            uint32_t edge[]={0x64808080,0x00c2012f,0x7dea00f8,0x00260004};
            shinka_menu_wide_rect(cost,4,0,band,0,band,319,band+239,margin);
            shinka_menu_wide_rect(prose,4,0,band,0,band,319,band+239,margin);
            shinka_menu_wide_rect(edge,4,0,band,0,band,319,band+239,margin);
            CHECK((int16_t)cost[1]+9==(int16_t)edge[1]); /* last glyph stays inside the border */
            CHECK((int16_t)prose[1]==294-margin);
        }
    }
    for(int band=0;band<=256;band+=256) for(int margin=1;margin<=160;++margin) {
        /* Captured Status layouts: the summary's last equipment row occupies
         * the same lower band as the selector's full-width description.
         * Digivolution numbers extend past x=148; equipment tabs start at120. */
        const int cases[][4]={
            {SHINKA_STATUS_CHARACTER,193,207,1},
            {SHINKA_STATUS_CHARACTER,58,213,-1},
            {SHINKA_STATUS_CHARACTER_SELECT,170,199,-1},
            {SHINKA_STATUS_CHARACTER_SELECT,160,212,-1},
            {SHINKA_STATUS_DIGIVOLVE,153,125,1},
            {SHINKA_STATUS_DIGIVOLVE,182,212,1},
            {SHINKA_STATUS_DIGIVOLVE,117,104,1},
            {SHINKA_STATUS_DIGIVOLVE,236,104,1},
            {SHINKA_STATUS_CHARACTER_TECHNIQUES,153,93,1},
            {SHINKA_STATUS_CHARACTER_TECHNIQUES,182,178,1},
            {SHINKA_STATUS_CHARACTER_TECHNIQUES,170,199,-1},
            {SHINKA_STATUS_CHARACTER_TECHNIQUES,117,70,1},
            {SHINKA_STATUS_CHARACTER_TECHNIQUES,236,70,1},
            {SHINKA_STATUS_EQUIPMENT,120,58,1},
            {SHINKA_STATUS_EQUIPMENT,116,20,-1},
            {SHINKA_STATUS_EQUIPMENT,170,199,-1}
        };
        mode=0x1000;root_menu=0;options[2]=1;
        for(unsigned i=0;i<sizeof(cases)/sizeof(*cases);++i) {
            items_menu=cases[i][0];shinka_view_tick();CHECK(frontend);
            uint32_t glyph[]={0x64808080,((unsigned)cases[i][2]<<16)|(unsigned)cases[i][1],
                0x3a170000,0x000c0008};
            CHECK(!shinka_menu_wide_rect(glyph,4,0,band,0,band,319,band+239,margin));
            CHECK((int16_t)glyph[1]==cases[i][1]+cases[i][3]*margin);
            CHECK(glyph[2]==0x3a170000 && glyph[3]==0x000c0008);
        }
        items_menu=SHINKA_STATUS_DIGIVOLVE;shinka_view_tick();
        /* The base-partner tab, label and cursor must join the right list. */
        for(int x=74;x<=162;x+=22) {
            uint32_t tab[]={0x64808080,0x00440000u|(unsigned)x,0x7de96024,0x001c0018};
            shinka_menu_wide_rect(tab,4,0,band,0,band,319,band+239,margin);
            CHECK((int16_t)tab[1]==x+margin);
        }
        uint32_t name[]={0x64808080,0x004d005f,0x3a171e28,0x000c0008};
        shinka_menu_wide_rect(name,4,0,band,0,band,319,band+239,margin);
        CHECK((int16_t)name[1]==95+margin);
        for(int page=SHINKA_STATUS_CHARACTER;page<=SHINKA_STATUS_CHARACTER_SELECT;++page) {
            items_menu=page;shinka_view_tick();
            for(int y=19;y< (page==SHINKA_STATUS_CHARACTER ? 46 : 32);++y) {
                uint32_t prompt[]={0x64808080,((unsigned)y<<16)|152,0x3a171218,0x000c0008};
                shinka_menu_wide_rect(prompt,4,0,band,0,band,319,band+239,margin);
                CHECK((int16_t)prompt[1]==152+margin+24);
            }
        }
        items_menu=SHINKA_STATUS_DIGIVOLVE;shinka_view_tick();
        uint32_t fill[]={0x64808080,0x00770078,0x7dea9690,0x00160028};
        uint32_t border[]={0x64808080,0x007700a0,0x7dea80c8,0x006c0018};
        int width=shinka_menu_wide_rect(fill,4,0,band,0,band,319,band+239,margin);
        CHECK(!shinka_menu_wide_rect(border,4,0,band,0,band,319,band+239,margin));
        CHECK(width==0 && (int16_t)fill[1]==120+margin
            && (int16_t)fill[1]+40==(int16_t)border[1]);
        CHECK(fill[2]==0x7dea9690 && fill[3]==0x00160028);
        for(int y=63;y<=97;y+=34) {
            items_menu=y==63 ? SHINKA_STATUS_CHARACTER_TECHNIQUES : SHINKA_STATUS_DIGIVOLVE;
            uint32_t bridge[]={0x64808080,((unsigned)y<<16)|200,0x7dea9690,0x00160028};
            CHECK(shinka_menu_wide_rect(bridge,4,0,band,0,band,319,band+239,margin)==0);
            CHECK((int16_t)bridge[1]==200+margin && bridge[3]==0x00160028);
        }
        /* Compact Status header pieces share their endpoints and retain UVs. */
        int end=144+margin;
        for(int x=20;x<352;x=x==20 ? 64 : x+32) {
            uint32_t header[]={0x64808080,0x000d0000u|(unsigned)x,0x7deac62c,
                0x00270000u|(x==20 ? 44u : 32u)};
            int span=shinka_menu_wide_rect(header,4,0,band,0,band,319,band+239,margin);
            CHECK((int16_t)header[1]==end && span>0);end+=span;
        }
        CHECK(end==352+margin);
        options[2]=0;shinka_view_tick();
        uint32_t original[]={0x64808080,0x00770078,0x7dea9690,0x00160028};
        CHECK(!shinka_menu_wide_rect(original,4,0,band,0,band,319,band+239,margin));
        CHECK(original[1]==0x00770078 && original[3]==0x00160028);
    }
    for(int margin=1;margin<=160;++margin) for(int band=0;band<=256;band+=256) {
        const unsigned backgrounds[]={0x3ae91a28,0x3b2b00a8,0x3b6b0078,0x3f6b0060,0x3fab0030,0x3feb0000,0x7d28ba30,0x7d68bb00,0x7d2a3814};
        for(int layer=0;layer<9;++layer) {
            mode=layer<3 ? 0x400 : layer<6 ? 0x1200 : 0xd01;
            items_menu=layer<3 ? SHINKA_FOLDER_SELECT : layer<6 ? SHINKA_CARD_ALBUM : SHINKA_LAB;
            options[2]=1;shinka_view_tick();CHECK(frontend);
            for(int x=0;x<384;x+=48) {
                uint32_t tile[]={0x64808080,(unsigned)x,backgrounds[layer],0x00300030};
                int width=shinka_menu_wide_rect(tile,4,0,band,0,band,319,band+239,margin);
                CHECK((int16_t)tile[1]==x && width==0);
                CHECK(tile[2]==backgrounds[layer] && tile[3]==0x00300030);
            }
        }
        mode=0x400;items_menu=SHINKA_FOLDER_EDIT;shinka_view_tick();
        for(int col=0;col<9;++col) {
            uint32_t card[]={0x64808080,0x003a0010u+(unsigned)col*32,0x40300000,0x00200020};
            uint32_t cursor[]={0x64808080,0x0038000fu+(unsigned)col*32,0x3baa7400,0x00230024};
            shinka_menu_wide_rect(card,4,0,band,0,band,319,band+239,margin);
            shinka_menu_wide_rect(cursor,4,0,band,0,band,319,band+239,margin);
            CHECK((int16_t)card[1]-(int16_t)cursor[1]==1);
            CHECK((int16_t)card[1]==16+col*32);
        }
        /* Last-row footer strips and glyphs retain their shared native span. */
        for(int y=185;y<=218;++y) for(int x=144;x<=304;x+=8) {
            uint32_t footer[]={0x64808080,((unsigned)y<<16)|(unsigned)x,0x3a681400,0x000c0008};
            CHECK(!shinka_menu_wide_rect(footer,4,0,band,0,band,319,band+239,margin));
            CHECK((int16_t)footer[1]==x);
        }
        uint32_t folder_name[]={0x64808080,0x00180016,0x3a1715d8,0x000c0008};
        shinka_menu_wide_rect(folder_name,4,0,band,0,band,319,band+239,margin);
        CHECK((int16_t)folder_name[1]==22*(320+2*margin)/320-margin+4);
        items_menu=SHINKA_FOLDER_CARDS;shinka_view_tick();
        for(int y=23;y<220;y+=11) for(int x=74;x<=320;x+=7) {
            uint32_t list[]={0x64808080,((unsigned)y<<16)|(unsigned)x,0x3a170000,0x000c0008};
            CHECK(!shinka_menu_wide_rect(list,4,0,band,0,band,319,band+239,margin));
            CHECK((int16_t)list[1]==x);
        }
        items_menu=SHINKA_FOLDER_EXPLAIN;shinka_view_tick();
        uint32_t prose1[]={0x64808080,0x00170088,0x3a170000,0x000c0008};
        uint32_t prose2[]={0x64808080,0x0018008f,0x3a170000,0x000c0008}; /* descender baseline */
        shinka_menu_wide_rect(prose1,4,0,band,0,band,319,band+239,margin);
        shinka_menu_wide_rect(prose2,4,0,band,0,band,319,band+239,margin);
        CHECK((int16_t)prose2[1]-(int16_t)prose1[1]==7); /* explanation crosses x=140 intact */
        items_menu=SHINKA_FOLDER_SELECT;shinka_view_tick();
        /* All 16 palette frames share identical geometry on all three rows,
         * including the diagonal join and the far right lower strip. */
        const unsigned outline[][5]={
            {23,0,20,39,0x14},{43,0,32,39,0x732c},{75,0,32,39,0x732c},
            {107,0,32,39,0x732c},{139,0,32,39,0x732c},{171,0,28,39,0xab00},
            {199,15,20,24,0x2d88},{219,15,20,24,0x2d88},
            {239,15,20,24,0x2d88},{259,15,20,24,0x2d88},{279,15,36,24,0xc788}
        };
        for(unsigned palette=0x3c29;palette<=0x3fe9;palette+=64)
            for(unsigned row=0;row<3;++row) {
                int end=23*(320+2*margin)/320-margin;
                for(unsigned i=0;i<sizeof(outline)/sizeof(*outline);++i) {
                    const unsigned *p=outline[i];
                    uint32_t piece[]={0x64808080,((80+45*row+p[1])<<16)|p[0],
                        (palette<<16)|p[4],(p[3]<<16)|p[2]};
                    uint32_t uv=piece[2],size=piece[3];
                    int span=shinka_menu_wide_rect(piece,4,0,band,0,band,319,band+239,margin);
                    CHECK((int16_t)piece[1]==end && span>0);
                    CHECK(piece[2]==uv && piece[3]==size);
                    end+=span;
                }
                CHECK(end==315*(320+2*margin)/320-margin);
            }
        for(int y=83;y<=173;y+=45) {
            uint32_t name[]={0x64808080,((unsigned)y<<16)|29,0x3a1715d8,0x000c0008};
            shinka_menu_wide_rect(name,4,0,band,0,band,319,band+239,margin);
            CHECK((int16_t)name[1]==29*(320+2*margin)/320-margin+4);
        }
        int end=123+margin;
        for(int x=123;x<=347;x+=32) {
            uint32_t ribbon[]={0x64808080,0x001c0000u|(unsigned)x,0x39a80084,0x00190020};
            CHECK(!shinka_menu_wide_rect(ribbon,4,0,band,0,band,319,band+239,margin));
            CHECK((int16_t)ribbon[1]==end);end+=32;
        }
        mode=0xd01;items_menu=SHINKA_LAB;shinka_view_tick();
        uint32_t translucent[]={0x66808080,0x009c00d5,0x27572ad4,0x00140020};
        shinka_menu_wide_rect(translucent,4,0,band,0,band,319,band+239,margin);
        CHECK((int16_t)translucent[1]==213+margin && translucent[3]==0x00140020);
        items_menu=SHINKA_LAB_LOAD;shinka_view_tick();
        uint32_t tech1[]={0x64808080,0x005e0088,0x3a170000,0x000c0008};
        uint32_t tech2[]={0x64808080,0x005e008f,0x3a170000,0x000c0008};
        shinka_menu_wide_rect(tech1,4,0,band,0,band,319,band+239,margin);
        shinka_menu_wide_rect(tech2,4,0,band,0,band,319,band+239,margin);
        CHECK((int16_t)tech1[1]==136+margin && (int16_t)tech2[1]-(int16_t)tech1[1]==7);
        uint32_t mp[]={0x64808080,0x00d10109,0x3a170000,0x000c0008};
        shinka_menu_wide_rect(mp,4,0,band,0,band,319,band+239,margin);CHECK((int16_t)mp[1]==265+margin);
        items_menu=SHINKA_LAB_CHART;shinka_view_tick();
        const unsigned shoulder_x[]={40,47,278,285};
        for(unsigned palette=0x7d29;palette<=0x7de9;palette+=64) for(int side=0;side<2;++side) {
            int x=side ? 272 : 23;
            uint32_t arrow[]={0x64808080,0x00c90000u|(unsigned)x,
                (palette<<16)|(side ? 0x5868u : 0xed00u),0x00100024};
            shinka_menu_wide_rect(arrow,4,0,band,0,band,319,band+239,margin);
            CHECK((int16_t)arrow[1]==x+(side ? margin : -margin));
        }
        for(unsigned i=0;i<4;++i) {
            uint32_t glyph[]={0x64808080,0x00c40000u|shoulder_x[i],0x3a170000,0x000c0008};
            shinka_menu_wide_rect(glyph,4,0,band,0,band,319,band+239,margin);
            CHECK((int16_t)glyph[1]==(int)shoulder_x[i]+(i<2 ? -margin : margin));
        }
        for(int x=0;x<=320;x+=8) {
            uint32_t cap[]={0x64808080,0x00110000u|(unsigned)x,0x7cabc188,0x001e0014};
            shinka_menu_wide_rect(cap,4,0,band,0,band,319,band+239,margin);
            CHECK((int16_t)cap[1]==x-margin);
            uint32_t hint[]={0x64808080,0x00cf0000u|(unsigned)x,0x3a170000,0x000c0008};
            shinka_menu_wide_rect(hint,4,0,band,0,band,319,band+239,margin);
            CHECK((int16_t)hint[1]==x);
        }
        uint32_t node[]={0x64808080,0x00320014,0x7ca84000,0x00200020};
        shinka_menu_wide_rect(node,4,0,band,0,band,319,band+239,margin);
        CHECK(node[1]==0x00320014); /* chart connectors and nodes stay in one coordinate system */
        items_menu=SHINKA_LAB_TECHNIQUES;shinka_view_tick();
        uint32_t bridge[]={0x64808080,0x00640088,0x7cab007c,0x00820020};
        uint32_t divider[]={0x64808080,0x006400a8,0x7cab0028,0x00820028};
        CHECK(shinka_menu_wide_rect(bridge,4,0,band,0,band,319,band+239,margin)==0);
        shinka_menu_wide_rect(divider,4,0,band,0,band,319,band+239,margin);
        CHECK((int16_t)bridge[1]==136+margin && (int16_t)bridge[1]+32==(int16_t)divider[1]);
        uint32_t pane[]={0x64808080,0x006400d0,0x7cab009c,0x0082001c};
        CHECK(shinka_menu_wide_rect(pane,4,0,band,0,band,319,band+239,margin)==0);
        CHECK((int16_t)pane[1]==208+margin && pane[2]==0x7cab009c);
        uint32_t skill[]={0x64808080,0x008c00b0,0x3a171e28,0x000c0008};
        shinka_menu_wide_rect(skill,4,0,band,0,band,319,band+239,margin);
        CHECK((int16_t)skill[1]==176+margin);
        options[2]=0;shinka_view_tick();
        uint32_t panel[]={0x64808080,0x00130000,0x7cabb800,0x00350028};
        CHECK(!shinka_menu_wide_rect(panel,4,0,band,0,band,319,band+239,margin));CHECK(panel[1]==0x00130000);
    }
    mode=0x1000;items_menu=SHINKA_STATUS_MAP;options[2]=1;shinka_view_tick();CHECK(frontend);
    for(int band=0;band<=256;band+=256) for(map_pan=-72;map_pan<=0;++map_pan) {
        /* Captured map strips, paired icon layers and free cursor. At 16:9
         * every world point is independent of the native camera position. */
        const unsigned palettes[]={0x40140000,0x40540000,0x7f3b6000,0x7d7088d8,0x7eb058d8,0x7d722020};
        for(unsigned i=0;i<sizeof(palettes)/sizeof(*palettes);++i) {
            uint32_t sprite[]={0x64808080,0x00600000u|(uint16_t)(100+map_pan),palettes[i],0x00180018};
            CHECK(!shinka_menu_wide_rect(sprite,4,0,band,0,band,319,band+239,53));
            CHECK((int16_t)sprite[1]==64);
            CHECK(sprite[2]==palettes[i] && sprite[3]==0x00180018);
        }
        uint32_t tooltip[]={0x64808080,0x00140009,0x7e2b40b0,0x00280008};
        uint32_t text[]={0x64808080,0x001a0010,0x3a170000,0x000c0008};
        shinka_menu_wide_rect(tooltip,4,0,band,0,band,319,band+239,53);
        shinka_menu_wide_rect(text,4,0,band,0,band,319,band+239,53);
        CHECK((int16_t)tooltip[1]==9-53 && (int16_t)text[1]==16-53);
    }
    options[2]=0;shinka_view_tick();
    { uint32_t sprite[]={0x64808080,0x00600064,0x7eb058d8,0x00180018};
      CHECK(!shinka_menu_wide_rect(sprite,4,0,0,0,0,319,239,53));CHECK(sprite[1]==0x00600064); }
    items_menu=SHINKA_STATUS_ITEMS;options[2]=0;shinka_view_tick();
    CHECK(!frontend);
    { uint32_t glyph[]={0x64808080,0x002500bc,0x3a170000,0x000c0008};
      CHECK(!shinka_menu_wide_rect(glyph,4,0,0,0,0,319,239,53));CHECK(glyph[1]==0x002500bc); }
    items_menu=0;options[2]=1;shinka_view_tick();
    CHECK(!frontend);
    started=1;mode=0x600;options[0]=1;shinka_view_tick();
    for(int band=0;band<=256;band+=256) {
        uint32_t panel[]={0x64808080,0x001400CB,0x3E2059C4,0x001C0018};
        shinka_battle_hud_command(panel,4,0,band,0,band,319,band+239,53);
        CHECK(panel[1]==0x00140100 && panel[2]==0x3E2059C4 && panel[3]==0x001C0018);
        uint32_t bar[]={0x38287100,0x0025008F,0x003EC800,0x0025000F,0x00287100,0x002B008F,0x003EC800,0x002B000F};
        shinka_battle_hud_command(bar,8,0,band,0,band,319,band+239,53);
        CHECK(bar[1]==0x0025005A && bar[3]==0x0025FFDA && bar[5]==0x002B005A && bar[7]==0x002BFFDA);
        uint32_t description[]={0x64808080,0x00D00125,0x3B171580,0x000C0008};
        shinka_battle_hud_command(description,4,0,band,0,band,319,band+239,53);
        CHECK(description[1]==0x00D0015E); /* MP cost follows the right box edge */
        uint32_t prose[]={0x64808080,0x00D00125,0x3A171580,0x000C0008};
        shinka_battle_hud_command(prose,4,0,band,0,band,319,band+239,53);
        CHECK(prose[1]==0x00D000ED); /* long ordinary dialogue does not split */
        /* Captured pulse palettes: each must retain one anchor in both buffers,
         * at every supported width. Ordinary text/other textures stay left. */
        const unsigned advance_cluts[]={0x3057,0x3097,0x30d7,0x3117,0x3157};
        for(unsigned c=0;c<5;++c) for(int margin=1;margin<=160;++margin) {
            uint32_t advance[]={0x64808080,0x00D00123,
                (advance_cluts[c]<<16)|0x3c54,0x000C000C};
            shinka_battle_hud_command(advance,4,0,band,0,band,319,band+239,margin);
            CHECK(advance[1]==(0x00D00000u|(291u+margin+4)));
            CHECK(advance[2]==((advance_cluts[c]<<16)|0x3c54) && advance[3]==0x000C000C);
        }
        for(int unrelated=0;unrelated<3;++unrelated) {
            uint32_t sprite[]={0x64808080,0x00D00123,0x30D73C54,0x000C000C};
            if(unrelated==0) sprite[2]^=1; /* different texture */
            if(unrelated==1) sprite[2]=0x30d63c54; /* different CLUT column */
            if(unrelated==2) sprite[2]=0x31973c54; /* outside pulse rows */
            shinka_battle_hud_command(sprite,4,0,band,0,band,319,band+239,53);
            CHECK(sprite[1]==0x00D000EB);
        }
        options[0]=0;shinka_view_tick();
        for(unsigned c=0;c<5;++c) {
            uint32_t advance[]={0x64808080,0x00D00123,(advance_cluts[c]<<16)|0x3c54,0x000C000C};
            shinka_battle_hud_command(advance,4,0,band,0,band,319,band+239,53);
            CHECK(advance[1]==0x00D00123);
        }
        options[0]=1;shinka_view_tick();
        for(int margin=1;margin<=160;++margin) {
            int x=0, previous=8-margin;
            const int xs[]={11,19,83,147,211,275};
            for(int tile=0;tile<6;++tile) {
                uint32_t words[]={0x64808080,0x00bc0000u|xs[tile],
                    tile==0 ? 0x3e617de0u : tile==5 ? 0x3e614670u : 0x3e6120bcu,
                    0x00260000u|(tile==0 ? 8 : tile==5 ? 32 : 64)};
                int width=shinka_battle_dialogue_tile(words,4,0,band,0,band,319,band+239,margin,&x);
                CHECK(width>0 && x==previous);
                if(tile==0 || tile==5) CHECK(width==(tile==0 ? 8 : 32));
                previous=x+width;
                CHECK(!shinka_battle_dialogue_tile(words,4,160,band,0,band,319,band+239,margin,&x));
                CHECK(!shinka_battle_dialogue_tile(words,4,0,band,0,band,319,band+239,0,&x));
                words[2]^=1; /* unrelated texture must not stretch */
                CHECK(!shinka_battle_dialogue_tile(words,4,0,band,0,band,319,band+239,margin,&x));
            }
            CHECK(previous==311+margin);
        }
        uint32_t cap[]={0x64808080,0x003E0082,0x3EA05940,0x00150020};
        shinka_battle_hud_command(cap,4,0,band,0,band,319,band+239,53);
        CHECK(cap[1]==0x003E004D); /* 162px list edge must not split at x=160 */
        uint32_t tag[]={0x64808080,0x00500098,0x3EA05940,0x000C0060};
        shinka_battle_hud_command(tag,4,0,band,0,band,319,band+239,53);
        CHECK(tag[1]==0x00500063); /* Tag bars crossing the midpoint stay together */
        uint32_t portrait[]={0x66808080,0x004A00CE,0x3EE30000,0x00400068};
        shinka_battle_hud_command(portrait,4,0,band,0,band,319,band+239,53);
        CHECK(portrait[1]==0x004A0103);
        uint32_t tl=0xe3000000u|208u|((76u+band)<<10);
        uint32_t br=0xe4000000u|307u|((135u+band)<<10);
        uint32_t origin=0xe5000000u|258u|((106u+band)<<11);
        shinka_battle_hud_command(&tl,1,0,band,0,band,319,band+239,53);
        shinka_battle_hud_command(&br,1,0,band,261,band+76,319,band+239,53);
        shinka_battle_hud_command(&origin,1,0,band,261,band+76,360,band+135,53);
        CHECK((tl&1023)==261 && (br&1023)==360 && (origin&2047)==311);
        CHECK(shinka_battle_hud_portrait(261,band+76,360,band+135,53));
        CHECK(!shinka_battle_hud_portrait(261,band+76,359,band+135,53));
        for(int tile=0;tile<12;++tile)
            CHECK(shinka_battle_hud_cursor(tile*12,244,14,band+69,12,12,53));
        CHECK(!shinka_battle_hud_cursor(144,244,14,band+69,12,12,53));
        CHECK(!shinka_battle_hud_cursor(13,244,14,band+69,12,12,53));
        CHECK(!shinka_battle_hud_cursor(48,240,14,band+69,12,12,53));
        CHECK(shinka_battle_hud_cursor(48,244,168,band+147,12,12,53));
        CHECK(!shinka_battle_hud_cursor(48,244,320,band+69,12,12,53));
    }
    for(int scenario=0;scenario<4;++scenario) {
        uint32_t sprite[]={0x64808080,0x006D0025,0x3A1715D8,0x000C0008};
        mode=scenario==0 ? 0x21d : 0x600;
        shinka_battle_hud_command(sprite,4,scenario==1 ? 160 : 0,scenario==1 ? 120 : 0,
            0,0,319,239,scenario==2 ? 0 : 53);
        CHECK(sprite[1]==(scenario==3 ? 0x006DFFF0u : 0x006D0025u));
    }
    animation_tests();
    puts("Field preview, battle projection, scene isolation and independent settings passed.");
    return 0;
}
