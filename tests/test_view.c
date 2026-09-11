#include <stdio.h>
#include <stdlib.h>
#include "view.h"
#include "battle_hud.h"
#include "menu_wide.h"
#define CHECK(c) do { if (!(c)) { fprintf(stderr,"line %d: %s\n",__LINE__,#c); exit(1); } } while (0)
static uint32_t mode;
static uint32_t previous_mode, language = 2, destination = 2;
static int started = 1, options[3], frontend;
static int root_menu;
static int items_menu;
int shinka_menu_root_active(void) { return root_menu; }
int shinka_menu_items_active(void) { return items_menu; }
int shinka_menu_status_layout(void) { return items_menu; }
int psx_mod_game_started(void) { return started; }
uint32_t psx_mod_read_word(uint32_t addr) {
    if (addr == 0x8004b3f8) return mode;
    if (addr == 0x8004b400) return previous_mode;
    if (addr == 0x8005cca8) return language;
    CHECK(addr == 0x8005ccf0); return destination;
}
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
    /* A repeating tile must keep its sampling width throughout a scroll.
     * Sharing integer edges alone allowed 63/64px breathing at 16:9. */
    for(int scene=0;scene<4;++scene) for(int band=0;band<=256;band+=256) {
        const uint32_t status_layers[]={0x7da81060,0x7deb1090,0x7da93000};
        const uint32_t npc_layers[]={0x7ca7b850,0x7ce65828,0x7ce75858};
        mode=scene<2 ? (scene ? 0xf00 : 0xa00) : 0x1000;
        root_menu=scene==3;items_menu=scene==2;options[2]=1;shinka_view_tick();
        for(int layer=0;layer<3;++layer) for(int phase=-96;phase<96;++phase) {
            uint32_t texture=scene<2 ? npc_layers[layer] : status_layers[layer];
            int edge=0;
            for(int column=0;column<7;++column) {
                uint32_t tile[]={0x64808080,0x00200000u|(uint16_t)(phase+column*48),texture,0x00300030};
                int width=shinka_menu_wide_rect(tile,4,0,band,0,band,319,band+239,53);
                CHECK(width==64); /* constant texture scale, every phase and layer */
                if(column) CHECK((int16_t)tile[1]==edge);
                edge=(int16_t)tile[1]+width;
            }
        }
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
        CHECK(shinka_menu_wide_rect(tile,4,0,0,0,0,319,239,53)==64);
        CHECK((int16_t)tile[1]==-53); /* closing backdrop must repaint both margins */
        CHECK(!shinka_menu_wide_rect(panel,4,0,0,0,0,319,239,53));
        CHECK(panel[1]==0x00c20000); /* pending presentation isn't layout admission */
    }
    options[2]=0;CHECK(!shinka_view_wide_requested());shinka_view_tick();CHECK(!frontend);
    options[2]=1;
    for(unsigned row=0;row<8;++row) {
        destination=row;shinka_view_tick();CHECK(frontend==(row==0 || row==1 || row==3));
    }
    destination=0;language=3;shinka_view_tick();CHECK(!frontend);language=2;
    previous_mode=0x600;shinka_view_tick();CHECK(!frontend); /* stale row after a state load */
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
        mode=scenario==0 ? 0xd00 : 0x1000;destination=scenario==1 ? 2 : 0;
        if(scenario==2) wipe[2]^=1;
        if(scenario==3) wipe[2]=0x3dd65f40;
        options[2]=scenario==4 ? 0 : 1;shinka_view_tick();
        CHECK(!shinka_menu_wide_rect(wipe,4,0,0,0,0,319,239,53));
        CHECK(wipe[1]==0x003400c0);
    }
    options[2]=1;previous_mode=0;destination=2;
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
    puts("Field preview, battle projection, scene isolation and independent settings passed.");
    return 0;
}
