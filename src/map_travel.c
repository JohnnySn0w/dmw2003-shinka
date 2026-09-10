#include "cpu_state.h"
#include "mod_plugins.h"
#include "gpu.h"
#include "map_data.h"

extern int shinka_journal_enabled(void);
#define R psx_mod_read_word
#define B psx_mod_read_byte
#define W psx_mod_write_word
#define MODE 0x8004b3f8u
#define RETURN 0x80048d68u
#define STORY 0x8004b370u
#define PENDING 0x53485452u
#define CUT 0x53484354u
#define PAGE 5u
#define TEDDY_COMPLETE 0x8004b3e0u /* flag 0x4011, bit 1 */
#define KEITH_COMPLETE 0x8004b3e0u /* flag 0x4016, bit 6 */

struct arrival { uint32_t stage, x, y; };

/* Arrival points validated with the original loader.
 * Asuka uses the bridge, avoiding the plot-dependent Main Lobby entrance.
 * Flawe's published Fast Travel work supplied transition/arrival investigation
 * leads; this module implements its own guarded flow and destination policy. */
static const struct { uint32_t icon, stage, x, y; } destinations[] = {
    {20, 0x202, 0x2dda8, 0xf760}, /* Asuka City bridge */
    {30, 0x21d, 225700, 164434}, /* Central Park */
    {22, 0x21e, 111434, 91323},  /* Wire Forest Entrance */
    {21, 0x222, 87454, 66170},   /* Wire Forest */
    {15, 0x22e, 0x21fda, 0x1d3d8}, /* Seiryu City */
    {32, 0x232, 0x15ade, 0x111cd}, /* South Station, outside the gondola */
    {43, 0x234, 0x3dc56, 0x1f77c}, /* Bulk Bridge */
    {44, 0x237, 0x2d205, 0x106a6}, /* Tranquil Swamp */
    {26, 0x249, 84211, 84884},   /* Pelche Oasis */
};
static int object(uint32_t p, uint32_t callback) {
    return p >= 0x80090000u && p <= 0x801eff00u && !(p & 3)
        && R(p + 0x28) == 0x80014274 && R(p + 0x48) == callback;
}
static int controller(uint32_t p) {
    return object(p, 0x80099894) && R(p + 0x20) == 3;
}
static uint32_t root_child(uint32_t parent) {
    uint32_t children=R(parent+0x24);
    return children >= 0x80090000u && children <= 0x801ffff4u && !(children & 3)
        ? R(children) : 0;
}
static int revision(void) {
    unsigned i,j;
    if (R(MODE) != 0x1000 || R(MODE + 4) || R(0x8005cca8) != 2) return 0;
    for (i=0;i<sizeof(map_guards)/sizeof(map_guards[0]);++i)
        for (j=0;j<map_guards[i].count;++j)
            if (R(map_guards[i].address+j*4) != map_guards[i].words[j]) return 0;
    for (i=0;i<sizeof(map_stage_icons);++i)
        if (B(0x8009b5fc+i) != map_stage_icons[i]) return 0;
    return 1;
}
static int destination(uint32_t icon) {
    unsigned i;
    for (i=0;i<sizeof(destinations)/sizeof(destinations[0]);++i)
        if (destinations[i].icon == icon) return (int)i;
    return -1;
}
static int visited(uint32_t stage) {
    unsigned bit=stage & 255;
    return (B(0x8004b3c0 + bit/8) >> (bit%8)) & 1;
}
static int source(uint32_t stage) {
    unsigned i;
    if (stage == 0x200) return 1; /* Asuka Main Lobby, including its outdoor approach */
    if (stage == 0x233) return 1; /* Bulk Swamp shares Bulk Bridge's map icon. */
    for (i=0;i<sizeof(destinations)/sizeof(destinations[0]);++i)
        if (destinations[i].stage == stage) return 1;
    return 0;
}
static const char* departure(uint32_t stage, uint32_t story) {
    /* WSTAG420 writes 5 after the badge. WSTAG395's Wind Prairie scene
     * requires 5 and flag 0x4011 clear; its completion sets that flag. */
    if (stage == 0x22e && story == 5 && !(B(TEDDY_COMPLETE) & 2))
        return "Use the city exit";
    return NULL;
}
static int south_stop(uint32_t stage) {
    return stage == 0x232 || stage == 0x233 || stage == 0x234 || stage == 0x237;
}
static struct arrival landing(int i, uint32_t story) {
    struct arrival a={destinations[i].stage,destinations[i].x,destinations[i].y};
    /* WSTAG205's Keith event completes flag 0x4016. Before it completes,
     * use the bridge approach identified by Flawe instead of its inner end. */
    if (a.stage == 0x202 && story == 6 && !(B(KEITH_COMPLETE) & 0x40)) {
        a.x=0x27e34; a.y=0x12bcc;
    }
    return a;
}
static const char* plan(uint32_t parent, uint32_t icon, struct arrival* out) {
    uint32_t story=R(STORY), stage=R(RETURN);
    const char* blocked;
    int i=destination(icon);
    if (!controller(parent)) return "Reopen menu for travel";
    if (!source(stage)) return "Travel unavailable here";
    /* Later campaign and post-game access need separate destination validation. */
    if (!story || story > 0x24) return "Travel unavailable now";
    blocked=departure(stage,story);
    if (blocked) return blocked;
    if (i < 0) return "No travel point yet";
    if (south_stop(stage) || south_stop(destinations[i].stage)) {
        /* WSTAG440's first South Station arrival (event 0x98) completes by
         * advancing story 6 to 7. A visible/visited map field alone can precede
         * completion; keep both departures and arrivals behind this check. */
        if (story < 7) return "Finish the gondola trip";
        if (!visited(0x232)) return "Visit South Station first";
    }
    if (!visited(destinations[i].stage)) return "Visit arrival area first";
    if (destinations[i].stage == stage) return "Already at this location";
    if (out) *out=landing(i,story);
    return NULL;
}
static uint16_t button(unsigned logical) {
    unsigned bit=B(0x8004b874+logical);
    return bit < 16 ? (uint16_t)(1u<<bit) : 0;
}
static void arrive(const struct arrival* a) {
    W(RETURN,a->stage);
    W(RETURN+4,a->x); W(RETURN+8,a->y);
}
/* Called after the frame's DrawSync, before display-buffer exchange. Clear both
 * original display rectangles before the loader reuses menu resources.
 * No texture area is touched. */
void shinka_map_present(void) {
    uint32_t owner, parent;
    struct arrival a;
    if (!revision()) return;
    owner=R(0x8005ccbc);
    if (!object(owner,0x80020b58) || R(owner+0x20) != 1) return;
    parent=root_child(owner);
    if (!object(parent,0x80083558) || R(parent+0x20) != 1) return;
    parent=root_child(parent);
    if (!controller(parent) || R(parent+0x78) != CUT) return;
    if (!shinka_journal_enabled() || plan(parent,R(parent+0x7c),&a)
        || R(parent+0x80) != R(RETURN) || R(parent+0x84) != R(STORY)
        || R(0x8004de48) != 0 || R(0x8004de4c) != 0x00f00140
        || R(0x8004de5c) != 0x01000000 || R(0x8004de60) != 0x00f00140) {
        W(parent+0x78,0); return;
    }
    gpu_write_gp0(0x02000000); gpu_write_gp0(0); gpu_write_gp0(0x00f00140);
    gpu_write_gp0(0x02000000); gpu_write_gp0(0x01000000); gpu_write_gp0(0x00f00140);
    arrive(&a);
    W(parent+0x78,0);
    /* Same queue as 80016b88. The mode owner recursively destroys Status and
     * its map before the next overlay loads; no root menu is constructed. */
    W(MODE+12,0); W(MODE+4,R(RETURN));
}
void shinka_map_allocate(CPUState* cpu) {
    if (shinka_journal_enabled() && cpu->gpr[31] == 0x80099aa4
        && cpu->gpr[4] == 0x80099894 && cpu->gpr[5] == 0x78
        && cpu->gpr[6] == 8 && revision()) {
        cpu->gpr[5]=0x88; /* pending marker, icon, source, story; serialized */
        cpu->gpr[6]=12;  /* extra null child distinguishes the extended allocation */
    }
}
void shinka_map_frame(CPUState* cpu) {
    uint32_t p, parent, root;
    if (cpu->gpr[31] != 0x80098c6c && cpu->gpr[31] != 0x800997ec) return;
    if (!revision()) return;
    if (cpu->gpr[31] == 0x80098c6c) {
        uint16_t pressed=psx_mod_read_half(0x8004b818), directions=0;
        unsigned i;
        p=cpu->gpr[17];
        if (!shinka_journal_enabled() || !object(p,0x8009913c)
            || R(p+0xc) != 1 || R(p+0x180) != 1 || R(p+0x78) != 0) return;
        parent=R(p+0x50);
        for (i=4;i<8;++i) directions |= button(i);
        if (!(pressed & button(13)) || (pressed & (directions | button(14)))
            || R(p+0x184) < 1 || R(p+0x184) > 46
            || R(p+0xa8+(R(p+0x184)-1)*4) != 1 || plan(parent,R(p+0x184),NULL)) return;
        /* Keep the map alive until this frame finishes drawing. */
        if (R(parent+0x78) == CUT) return;
        W(parent+0x78,CUT); W(parent+0x7c,R(p+0x184));
        W(parent+0x80,R(RETURN)); W(parent+0x84,R(STORY));
        psx_mod_write_half(0x8004b818,0);
    } else if (cpu->gpr[31] == 0x800997ec) {
        parent=cpu->gpr[16];
        if (!controller(parent) || R(parent+0x78) != PENDING) return;
        root=root_child(parent);
        if (object(root,0x8001270c) && R(root+0x20) == 0x2d
            && R(root+0xc) == 1 && R(root+0x10) == 3) {
            W(root+0xa0,PAGE); W(root+0xa4,parent);
        }
    }
}
void shinka_map_quick_menu(CPUState* cpu) {
    /* Compatibility for states saved during the former root-menu detour. */
    uint32_t p=cpu->gpr[4];
    if (R(MODE) == 0x1000 && object(p,0x8001270c) && R(p+0x20) == 0x2d
        && R(p+0xa0) == PAGE && R(p+0xc) == 1 && R(p+0x10) == 3
        && controller(R(p+0xa4)) && R(R(p+0xa4)+0x78) == PENDING)
        psx_mod_write_half(0x8004b818,button(14)); /* original full close animation */
}
void shinka_map_transition(CPUState* cpu) {
    uint32_t p=cpu->gpr[17], parent;
    struct arrival a;
    if (cpu->gpr[31] != 0x80013318 || !revision() || !object(p,0x8001270c)
        || R(p+0x20) != 0x2d || R(p+0xa0) != PAGE || cpu->gpr[4] != R(RETURN)) return;
    parent=R(p+0xa4);
    if (!controller(parent) || R(parent+0x78) != PENDING) return;
    if (shinka_journal_enabled() && !plan(parent,R(parent+0x7c),&a)
        && R(parent+0x80) == R(RETURN) && R(parent+0x84) == R(STORY)) {
        cpu->gpr[4]=a.stage;
        arrive(&a);
    }
    W(parent+0x78,0); W(p+0xa0,0); W(p+0xa4,0);
}

static uint32_t text_scratch;
void shinka_map_text(CPUState* cpu) {
    uint32_t p=cpu->gpr[16], table=cpu->gpr[5], icon=cpu->gpr[6], string;
    unsigned n=0, k;
    const char* help;
    uint8_t text[256];
    if (cpu->gpr[31] != 0x8009843c || !shinka_journal_enabled() || !revision()
        || !object(p,0x8009913c) || R(p+0x180) != 1 || icon != R(p+0x184)
        || icon < 1 || icon > 46 || table < 0x80090000 || table > 0x801f0000
        || R(table) < 47 || R(table) > 128) return;
    string=table+R(table+4+icon*4);
    if (string < table || string > 0x801fff00) return;
    for (k=0;k<96 && B(string+k);++k) {
        if (B(string+k)==2 && B(string+k+1)==1) {
            /* Some icons name two areas. Keep both names on the first line,
             * reserving the existing panel's second line for the travel hint. */
            text[n++]=1; text[n++]=1; text[n++]=1; text[n++]=13;
            text[n++]=1; text[n++]=1; ++k;
        } else text[n++]=B(string+k);
        if (n > 180) return;
    }
    if (!n || k >= 96) return;
    help=plan(R(p+0x50),icon,NULL);
    if (!help) help=icon == 20 ? "X: City entrance" : "X: Travel";
    text[n++]=2; text[n++]=1;
    while (*help && n < 252) {
        unsigned c=(unsigned char)*help++;
        if (c == ' ' || c == ':') { text[n++]=1; text[n++]=(uint8_t)(c == ' ' ? 1 : 7); }
        else text[n++]=(uint8_t)(c >= 'a' && c <= 'z' ? c-57 : c-51);
    }
    text[n++]=0;
    if (!text_scratch || R(text_scratch) != 0x4d415054) {
        text_scratch=psx_mod_alloc_guest_memory(260,4);
        if (!text_scratch) return;
        W(text_scratch,0x4d415054);
    }
    for (k=0;k<n;++k) psx_mod_write_byte(text_scratch+4+k,text[k]);
    cpu->gpr[5]=text_scratch+4; cpu->gpr[6]=0xffffffffu;
}
