#include "dev_nav.h"
#include <stddef.h>

extern uint32_t psx_read_word(uint32_t);
extern void psx_write_word(uint32_t, uint32_t);
extern uint8_t psx_read_byte(uint32_t);
extern void psx_write_byte(uint32_t, uint8_t);
#define R psx_read_word
#define W psx_write_word
#define MODE 0x8004b3f8u
#define RETURN 0x80048d68u
#define STORY 0x8004b370u
#define PARTY 0x8004949cu

static int field(uint32_t mode) { return mode >= 0x200 && mode < 0x300; }
static int object(uint32_t p, uint32_t callback) {
    return p >= 0x80090000 && p <= 0x801eff00 && !(p & 3)
        && R(p+0x28) == 0x80014274 && R(p+0x48) == callback;
}
static uint32_t first_child(uint32_t p) {
    uint32_t children=R(p+0x24);
    return children>=0x80090000 && children<=0x801ffffc && !(children&3)
        ? R(children) : 0;
}
const char* shinka_nav_lab(ShinkaNavLab* s) {
    uint32_t mode=R(MODE),owner=R(0x8005ccbc),root,action;
    unsigned i;
    if ((mode!=0xd00 && mode!=0xd01) || R(MODE+4)
        || R(0x80055d28)!=13 || R(0x8008ed0c)!=0x27bdff40)
        return "A supported stationary Digimon Lab overlay is required";
    if (!object(owner,0x80020b58) || R(owner+0x20)!=1)
        return "The native mode owner is not ready";
    root=first_child(owner);
    if (!object(root,0x80082f48) || R(root+0x20)!=1)
        return "The Digimon Lab module wrapper is not ready";
    root=first_child(root);
    if (!object(root,0x8008ed0c) || R(root+0x20)!=3)
        return "The Digimon Lab controller is not ready";
    s->root=root;s->lifecycle=R(root+0xc);s->phase=R(root+0x10);
    s->slot=R(root+0x64);
    for(i=0;i<3;++i) s->roster[i]=R(0x80048da4+i*4);
    s->action_menu=0;s->action_phase=0;s->action=0;
    action=first_child(root);
    if (object(action,0x8008a51c) && R(action+0x20)==19) {
        s->action_menu=action;s->action_phase=R(action+0x10);s->action=R(action+0x60);
    }
    return NULL;
}
static const char* ready(int expected_mode, int allow_menu) {
    uint32_t mode=R(MODE), owner=R(0x8005ccbc);
    if ((int)mode != expected_mode) return "Mode changed since the request was prepared";
    if (R(MODE+4)) return "An area transition is already queued";
    if (!field(mode) && !(allow_menu && mode == 0x1000 && field(R(RETURN))))
        return "Return to the field before using this command";
    if (!object(owner,0x80020b58) || R(owner+0x20) != 1)
        return "The native mode owner is not ready";
    return NULL;
}
void shinka_nav_state(ShinkaNavState* s) {
    uint32_t p;
    s->mode=R(MODE);s->queued=R(MODE+4);s->story=R(STORY);
    s->stage=R(RETURN);s->x=R(RETURN+4);s->y=R(RETURN+8);s->facing=R(RETURN+12);
    s->encounters=R(0x80042b1c);s->countdown=R(0x80048d64);s->quick_menu=0;
    s->quick_phase=0;s->quick_row=0;
    if (field(s->mode)) for (p=0x80090000;p<=0x801eff00;p+=4)
        if (object(p,0x8001270c) && R(p+0xc)==1 && R(p+0x20)==0x2d) {
            s->quick_menu=p;s->quick_phase=R(p+0x10);s->quick_row=R(p+0x58);break;
        }
}
const char* shinka_nav_warp(int stage,int x,int y,int facing,int expected_mode) {
    const char* error=ready(expected_mode,1);
    if (error) return error;
    /* Field-to-field loading chooses an entry trigger and ignores RETURN's
     * coordinates. Status-to-field loading restores that context instead. */
    if (R(MODE)!=0x1000) return "Open the map before queuing a coordinate warp";
    if (!field((uint32_t)stage) || x<0 || y<0 || x>0xffffff || y>0xffffff
        || facing<0 || facing>7) return "Invalid field destination or coordinates";
    /* Debug commands execute on the emulation thread. Queue LAST, as one
     * complete word; byte-at-a-time TCP writes can load a partial mode ID.
     * The existing mode owner tears down the old overlay and runs the loader. */
    W(RETURN,(uint32_t)stage);W(RETURN+4,(uint32_t)x);W(RETURN+8,(uint32_t)y);
    W(RETURN+12,(uint32_t)facing);W(MODE+12,0);W(MODE+4,(uint32_t)stage);
    return NULL;
}
const char* shinka_nav_enter(int stage,int expected_mode) {
    const char* error=ready(expected_mode,0);
    if (error) return error;
    /* Only the reciprocal exits traced in WSTAG485/500 are admitted here.
     * Unlike a map restore, native field entry resolves its own position. */
    if (!((expected_mode==0x23b && stage==0x23e)
        || (expected_mode==0x23e && stage==0x23b)))
        return "Unsupported native field connection";
    W(MODE+12,0);W(MODE+4,(uint32_t)stage);
    return NULL;
}
const char* shinka_nav_story(int value,int expected_mode) {
    const char* error=ready(expected_mode,0);
    if (error) return error;
    if (value<0 || value>255) return "Story must be 0..255";
    W(STORY,(uint32_t)value);return NULL;
}
const char* shinka_nav_flag(int flag,int value,int expected_mode) {
    uint32_t address,mask;
    const char* error=ready(expected_mode,0);
    if (error) return error;
    /* Only flags traced in the story audit. Other flag classes have distinct
     * storage; accepting an arbitrary ID here could overwrite another system. */
    if ((flag!=0x4006 && flag!=0x4011 && flag!=0x4016 && flag!=0x4018 && flag!=0x1c51)
        || (value!=0 && value!=1)) return "Unsupported story flag or value";
    /* Resident class-0x1c storage is distinct from class-0x40. WSTAG485's
     * event completion callback sets 0x1c51 through the native setter. */
    address=(flag==0x1c51?0x8004b3b5u:0x8004b3deu)+((unsigned)flag&0x1ff)/8;
    mask=1u<<((unsigned)flag%8);
    psx_write_byte(address,(uint8_t)((psx_read_byte(address)&~mask)|(value?mask:0)));
    return NULL;
}
const char* shinka_nav_encounters(int enabled,int expected_mode) {
    const char* error=ready(expected_mode,0);
    if (error) return error;
    if (enabled!=0 && enabled!=1) return "Encounters must be 0 or 1";
    /* Do not discard Shinka's countdown-unit marker. Off extends this field's
     * countdown; on makes the next ordinary random check eligible. Native
     * cutscene gates and scripted fights still apply. */
    W(0x80048d64,enabled?0:0x100000);return NULL;
}
void shinka_nav_partner(unsigned index,ShinkaNavPartner* p) {
    uint32_t a=PARTY+index*0x3dc, hp=R(a+0x20),mp=R(a+0x24);
    p->level=R(a+0x1c)&65535;p->hp=hp&65535;p->max_hp=hp>>16;
    p->mp=mp&65535;p->max_mp=mp>>16;p->strength=R(a+0x28)&65535;
}
static const char* stats_ready(int index,int expected_mode) {
    ShinkaNavPartner p;
    const char* error=ready(expected_mode,0);
    if (error) return error;
    if (index<0 || index>7) return "Partner index must be 0..7";
    /* Original resident profile accessor: stride 0x3dc, base 0x8004949c. */
    if (R(0x80017b4c)!=0x00041140 || R(0x80017b60)!=0x3c038005
        || R(0x80017b64)!=0x2463949c) return "Unsupported resident stat accessor";
    shinka_nav_partner((unsigned)index,&p);
    if (!p.level || p.level>99 || !p.max_hp || p.max_hp>9999 || p.max_mp>9999
        || p.hp>p.max_hp || p.mp>p.max_mp || p.strength>999)
        return "Partner stats are uninitialized or outside native limits";
    return NULL;
}
const char* shinka_nav_heal(int index,int expected_mode) {
    uint32_t a,hp,mp;
    const char* error=stats_ready(index,expected_mode);
    if (error) return error;
    a=PARTY+(unsigned)index*0x3dc;hp=R(a+0x20)>>16;mp=R(a+0x24)>>16;
    W(a+0x20,hp|(hp<<16));W(a+0x24,mp|(mp<<16));return NULL;
}
const char* shinka_nav_power(int index,int value,int expected_mode) {
    uint32_t a;
    const char* error=stats_ready(index,expected_mode);
    if (error) return error;
    if (value<1 || value>999) return "Strength must be 1..999";
    a=PARTY+(unsigned)index*0x3dc+0x28;
    W(a,(R(a)&0xffff0000u)|(uint32_t)value);return NULL;
}
