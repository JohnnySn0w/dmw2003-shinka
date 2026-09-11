#include <stdio.h>
#include <stdlib.h>
#include "view.h"
#include "battle_hud.h"
#include "menu_wide.h"
#define CHECK(c) do { if (!(c)) { fprintf(stderr,"line %d: %s\n",__LINE__,#c); exit(1); } } while (0)
static uint32_t mode;
static int started = 1, options[3], frontend;
static int root_menu;
static int items_menu;
int shinka_menu_root_active(void) { return root_menu; }
int shinka_menu_items_active(void) { return items_menu; }
int psx_mod_game_started(void) { return started; }
uint32_t psx_mod_read_word(uint32_t addr) { CHECK(addr == 0x8004b3f8); return mode; }
int shinka_view_get(int option) { return options[option]; }
void shinka_view_frontend(int wide) { frontend = wide; }
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
    for(int shop=0;shop<2;++shop) for(int band=0;band<=256;band+=256) {
        const uint32_t layers[]={0x7ca7b850,0x7ce65828,0x7ce75858};
        int previous=-1000;
        mode=shop ? 0xf00 : 0xa00;options[2]=1;shinka_view_tick();
        for(int x=-96;x<=384;++x) {
            int reference=0, reference_width=0;
            for(int layer=0;layer<3;++layer) {
                uint32_t tile[]={0x64808080,0x002b0000u|(uint16_t)x,layers[layer],0x00300030};
                int width=shinka_menu_wide_rect(tile,4,0,band,0,band,319,band+239,53);
                int position=(int16_t)tile[1];
                CHECK(width>0);
                CHECK(tile[2]==layers[layer] && tile[3]==0x00300030);
                if(!layer) { reference=position;reference_width=width; }
                else CHECK(position==reference && width==reference_width);
            }
            if(previous!=-1000) CHECK(reference-previous==1 || reference-previous==2);
            previous=reference; /* no column-boundary jump during scrolling */
        }
    }
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
        if (fullscreen) for (int settle=0;settle<8;++settle) shinka_view_tick();
        CHECK(frontend==!fullscreen); /* full-screen map/status child settles to 4:3 */
    }
    /* A mode-0x1000 task rebuild must not flash the window to 4:3 before the
     * root/Items object is discoverable; unresolved Status pages settle back. */
    started=1;mode=0x21d;root_menu=1;options[2]=1;shinka_view_tick();
    root_menu=0;mode=0x1000;
    for(int frame=0;frame<8;++frame) { shinka_view_tick();CHECK(frontend); }
    shinka_view_tick();CHECK(!frontend);
    root_menu=1;shinka_view_tick();CHECK(frontend);
    mode=0x1000;items_menu=1;options[2]=1;shinka_view_tick();CHECK(frontend);
    for(int layer=0;layer<3;++layer) {
        uint32_t tile[]={0x64808080,0x0000001c,layer==0?0x7da81060:layer==1?0x7deb1090:0x7da93000,0x00300030};
        int width=shinka_menu_wide_rect(tile,4,0,0,0,0,319,239,53);
        CHECK(width==64);
        CHECK((int16_t)tile[1]==-16);
    }
    for(int margin=1;margin<=160;++margin) {
        const unsigned backgrounds[]={0x7da81060,0x7deb1090,0x7da93000};
        int previous=-1000;
        for(int x=-96;x<=384;++x) {
            int reference=0, reference_width=0;
            for(int layer=0;layer<3;++layer) {
                uint32_t tile[]={0x64808080,0x00000000u|(uint16_t)x,backgrounds[layer],0x00300030};
                int width=shinka_menu_wide_rect(tile,4,0,0,0,0,319,239,margin);
                int position=(int16_t)tile[1];
                CHECK(width>0);
                if(!layer) { reference=position;reference_width=width; }
                else CHECK(position==reference && width==reference_width);
            }
            if(previous!=-1000) CHECK(reference-previous==1 || reference-previous==2);
            previous=reference;
        }
    }
    root_menu=0;items_menu=1;shinka_view_tick();CHECK(frontend);
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
            int end=-margin;
            for(int x=0;x<384;x+=48) {
                uint32_t tile[]={0x64808080,0x00200000u|(unsigned)x,backgrounds[layer],0x00300030};
                int width=shinka_menu_wide_rect(tile,4,0,band,0,band,319,band+239,margin);
                CHECK((int16_t)tile[1]==end && width>0);
                CHECK(tile[2]==backgrounds[layer] && tile[3]==0x00300030);end+=width;
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
    options[2]=0;shinka_view_tick();
    for(int settle=0;settle<8;++settle) shinka_view_tick();
    CHECK(!frontend);
    { uint32_t glyph[]={0x64808080,0x002500bc,0x3a170000,0x000c0008};
      CHECK(!shinka_menu_wide_rect(glyph,4,0,0,0,0,319,239,53));CHECK(glyph[1]==0x002500bc); }
    items_menu=0;options[2]=1;shinka_view_tick();
    for(int settle=0;settle<8;++settle) shinka_view_tick();
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
    puts("Field preview, battle projection, scene isolation and independent settings passed.");
    return 0;
}
