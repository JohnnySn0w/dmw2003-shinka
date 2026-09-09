#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cpu_state.h"
#include "mod_plugins.h"
#include "map_data.h"
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"line %d: %s\n",__LINE__,#x); exit(1); } } while(0)
static uint8_t ram[0x200000], saved[0x200000];
static int enabled=1, watching;
static unsigned writes;
static unsigned gpu_count;
static uint32_t gpu_words[6];
void gpu_write_gp0(uint32_t word) { CHECK(gpu_count<6);gpu_words[gpu_count++]=word; }
#define MAP 0x800ac000u
#define PARENT 0x800ad000u
#define ROOT 0x800ae000u
#define RETURN 0x80048d68u
static uint8_t* ptr(uint32_t a) { CHECK(a >= 0x80000000 && a < 0x80200000); return ram+a-0x80000000; }
uint32_t psx_mod_read_word(uint32_t a) { uint32_t v;memcpy(&v,ptr(a),4);return v; }
uint16_t psx_mod_read_half(uint32_t a) { uint16_t v;memcpy(&v,ptr(a),2);return v; }
uint8_t psx_mod_read_byte(uint32_t a) { return *ptr(a); }
static void allowed(uint32_t a) {
    if (watching) CHECK(a == MAP+0xc || (a >= PARENT+0x78 && a < PARENT+0x88)
        || (a >= ROOT+0xa0 && a < ROOT+0xa8) || (a >= RETURN && a < RETURN+12)
        || a == 0x8004b3fc || a == 0x8004b404
        || a == 0x8004b818 || (a >= 0x801f0000 && a < 0x801f0200));
    ++writes;
}
void psx_mod_write_word(uint32_t a,uint32_t v) { allowed(a);memcpy(ptr(a),&v,4); }
void psx_mod_write_half(uint32_t a,uint16_t v) { allowed(a);memcpy(ptr(a),&v,2); }
void psx_mod_write_byte(uint32_t a,uint8_t v) { allowed(a);*ptr(a)=v; }
uint32_t psx_mod_alloc_guest_memory(uint32_t size,uint32_t align) { CHECK(size<=512);return 0x801f0000; }
int shinka_journal_enabled(void) { return enabled; }
void shinka_map_allocate(CPUState*);
void shinka_map_frame(CPUState*);
void shinka_map_quick_menu(CPUState*);
void shinka_map_transition(CPUState*);
void shinka_map_text(CPUState*);
void shinka_map_present(void);
#define R psx_mod_read_word
#define W psx_mod_write_word
static CPUState cpu;
static void object(uint32_t p,uint32_t cb) { W(p+0x28,0x80014274);W(p+0x48,cb);W(p+0xc,1); }
static void fresh(void) {
    watching=0;enabled=1;gpu_count=0;memset(ram,0,sizeof(ram));memset(&cpu,0,sizeof(cpu));
    W(0x8004b3f8,0x1000);W(0x8005cca8,2);W(RETURN,0x249);
    W(RETURN+4,123456);W(RETURN+8,654321);W(0x8004b370,0x14);
    for(unsigned i=0;i<sizeof(map_guards)/sizeof(map_guards[0]);++i)
        for(unsigned j=0;j<map_guards[i].count;++j) W(map_guards[i].address+j*4,map_guards[i].words[j]);
    for(unsigned i=0;i<sizeof(map_stage_icons);++i) psx_mod_write_byte(0x8009b5fc+i,map_stage_icons[i]);
    memset(ptr(0x8004b3c0),255,30);
    for(unsigned i=0;i<16;++i) psx_mod_write_byte(0x8004b874+i,(uint8_t)i);
    object(MAP,0x8009913c);W(MAP+0x50,PARENT);W(MAP+0x180,1);W(MAP+0x184,30);W(MAP+0xa8+29*4,1);
    object(PARENT,0x80099894);W(PARENT+0x20,3);W(PARENT+0x24,0x800af000);W(0x800af000,ROOT);
    object(ROOT,0x8001270c);W(ROOT+0x20,0x2d);W(ROOT+0x10,3);
    object(0x800ab000,0x80020b58);W(0x800ab020,1);W(0x800ab024,0x800af010);
    W(0x800af010,0x800ab100);W(0x8005ccbc,0x800ab000);
    object(0x800ab100,0x80083558);W(0x800ab120,1);W(0x800ab124,0x800af014);W(0x800af014,PARENT);
    W(0x8004de4c,0x00f00140);W(0x8004de5c,0x01000000);W(0x8004de60,0x00f00140);
    psx_mod_write_half(0x8004b818,1<<13);watching=1;writes=0;
}
static void select_icon(void) { cpu.gpr[31]=0x80098c6c;cpu.gpr[17]=MAP;shinka_map_frame(&cpu); }
/* Older builds serialized a request while backing through the Status root. */
static void legacy_request(void) {
    W(MAP+0xc,3);W(PARENT+0x78,0x53485452);W(PARENT+0x7c,30);
    W(PARENT+0x80,R(RETURN));W(PARENT+0x84,psx_mod_read_byte(0x8004b370));
}
static void root_close(void) {
    cpu.gpr[31]=0x800997ec;cpu.gpr[16]=PARENT;shinka_map_frame(&cpu);
    CHECK(R(ROOT+0xa0)==5 && R(ROOT+0xa4)==PARENT);
    cpu.gpr[4]=ROOT;shinka_map_quick_menu(&cpu);CHECK(psx_mod_read_half(0x8004b818)==(1<<14));
}
static void transition(void) { cpu.gpr[31]=0x80013318;cpu.gpr[17]=ROOT;cpu.gpr[4]=R(RETURN);shinka_map_transition(&cpu); }
static void target(unsigned icon) {
    W(MAP+0x184,icon);W(MAP+0xa8+(icon-1)*4,1);
}
static void story_policy(void) {
    const unsigned icons[]={20,30,22,21,26};
    /* After the badge, every departure offered by the Seiryu map is rejected.
     * Other main-story phases still work. */
    for(unsigned story=4;story<=6;++story) for(unsigned i=0;i<5;++i) {
        fresh();watching=0;W(RETURN,0x22e);W(0x8004b370,story);target(icons[i]);watching=1;writes=0;
        select_icon();
        if(story==5) CHECK(writes==0 && R(PARENT+0x78)==0);
        else { shinka_map_present();CHECK(R(RETURN)!=0x22e && gpu_count==6); }
    }
    /* Completing the announcement releases travel immediately in phase 5.
     * A changed completion bit is rechecked even without a phase change. */
    for(unsigned legacy=0;legacy<2;++legacy) for(unsigned revoked=0;revoked<2;++revoked) {
        fresh();watching=0;W(RETURN,0x22e);W(0x8004b370,5);
        psx_mod_write_byte(0x8004b3e0,0xff);watching=1;
        if(legacy) { legacy_request();root_close(); } else select_icon();
        if(revoked) { watching=0;psx_mod_write_byte(0x8004b3e0,0xfd);watching=1; }
        if(legacy) transition();else shinka_map_present();
        CHECK(R(RETURN)==(revoked ? 0x22eu : 0x21du));
        CHECK(R(PARENT+0x78)==0 && R(0x8004b370)==5);
        CHECK(psx_mod_read_byte(0x8004b3e0)==(revoked ? 0xfd : 0xff));
    }
    /* An old queued departure cannot bypass the new policy after state load. */
    fresh();watching=0;W(RETURN,0x22e);W(0x8004b370,5);watching=1;
    legacy_request();root_close();transition();
    CHECK(R(RETURN)==0x22e && cpu.gpr[4]==0x22e && R(PARENT+0x78)==0);
    fresh();watching=0;W(RETURN,0x22e);W(0x8004b370,5);
    W(PARENT+0x78,0x53484354);W(PARENT+0x7c,30);W(PARENT+0x80,0x22e);W(PARENT+0x84,5);
    watching=1;shinka_map_present();CHECK(R(RETURN)==0x22e && gpu_count==0 && R(PARENT+0x78)==0);
    /* Players with an already-skipped event can still return to Seiryu. */
    fresh();watching=0;W(0x8004b370,5);target(15);watching=1;
    select_icon();shinka_map_present();CHECK(R(RETURN)==0x22e);
    /* Correct width: malformed/high story words must not alias an early phase. */
    fresh();watching=0;W(0x8004b370,0x105);watching=1;writes=0;
    select_icon();CHECK(writes==0);
    /* The incomplete interception uses the outer approach only in phase 6.
     * Unrelated bits in the same byte do not imply completion. */
    for(unsigned story=5;story<=7;++story) for(unsigned done=0;done<2;++done) {
        fresh();watching=0;W(0x8004b370,story);target(20);
        psx_mod_write_byte(0x8004b3e0,done ? 0xff : 0xbf);watching=1;
        select_icon();shinka_map_present();
        CHECK(R(RETURN)==0x202 && R(0x8004b3fc)==0x202);
        CHECK(R(RETURN+4)==(story==6 && !done ? 0x27e34u : 0x2dda8u));
        CHECK(R(RETURN+8)==(story==6 && !done ? 0x12bccu : 0xf760u));
    }
    /* Recompute the landing if a subflag changes without changing the phase.
     * Exercise both directions and the legacy pending-state completion path. */
    for(unsigned legacy=0;legacy<2;++legacy) for(unsigned done=0;done<2;++done) {
        fresh();watching=0;W(0x8004b370,6);target(20);
        psx_mod_write_byte(0x8004b3e0,done ? 0 : 0x40);watching=1;
        if(legacy) { legacy_request();W(PARENT+0x7c,20);root_close(); }
        else select_icon();
        watching=0;psx_mod_write_byte(0x8004b3e0,done ? 0x40 : 0);watching=1;
        if(legacy) transition();else shinka_map_present();
        CHECK(R(RETURN)==0x202 && R(RETURN+4)==(done ? 0x2dda8u : 0x27e34u));
        CHECK(R(0x8004b370)==6 && psx_mod_read_byte(0x8004b3e0)==(done ? 0x40 : 0));
    }
    /* Landing outside the lockdown is retained across both boundaries. */
    for(unsigned story=19;story<=24;++story) {
        fresh();watching=0;W(0x8004b370,story);target(20);watching=1;
        select_icon();shinka_map_present();CHECK(R(RETURN)==0x202 && R(RETURN+4)==0x2dda8);
    }
    /* The actual map panel presents the departure instruction, not X: Travel. */
    fresh();watching=0;W(RETURN,0x22e);W(0x8004b370,5);
    W(0x801e0000,47);W(0x801e0004+30*4,200);psx_mod_write_byte(0x801e00c8,14);
    watching=1;cpu.gpr[31]=0x8009843c;cpu.gpr[16]=MAP;cpu.gpr[5]=0x801e0000;cpu.gpr[6]=30;
    shinka_map_text(&cpu);
    {
        const char* expected="Use the city exit";
        uint32_t p=cpu.gpr[5]+3;
        for(unsigned i=0;expected[i];++i) {
            unsigned c=(unsigned char)expected[i];
            if(c==' ') { CHECK(psx_mod_read_byte(p++)==1);CHECK(psx_mod_read_byte(p++)==1); }
            else CHECK(psx_mod_read_byte(p++)==(c>='a' ? c-57 : c-51));
        }
        CHECK(psx_mod_read_byte(p)==0);
    }
}
int main(void) {
    story_policy();
    fresh();cpu.gpr[31]=0x80099aa4;cpu.gpr[4]=0x80099894;cpu.gpr[5]=0x78;cpu.gpr[6]=8;
    shinka_map_allocate(&cpu);CHECK(cpu.gpr[5]==0x88 && cpu.gpr[6]==12 && writes==0);
    fresh();select_icon();CHECK(R(MAP+0xc)==1 && R(RETURN)==0x249);
    CHECK(R(PARENT+0x78)==0x53484354 && R(0x8004b3fc)==0 && gpu_count==0);
    memcpy(saved,ram,sizeof(ram));writes=0;select_icon();CHECK(writes==0);
    fresh();memcpy(ram,saved,sizeof(ram));shinka_map_present(); /* pending state restore */
    CHECK(R(RETURN+4)==225700 && R(RETURN+8)==164434);
    CHECK(R(0x8004b3fc)==0x21d && R(0x8004b404)==0);
    CHECK(R(PARENT+0x78)==0 && R(ROOT+0xa0)==0); /* no root-menu detour */
    CHECK(gpu_count==6 && gpu_words[0]==0x02000000 && gpu_words[1]==0
        && gpu_words[2]==0x00f00140 && gpu_words[3]==0x02000000
        && gpu_words[4]==0x01000000 && gpu_words[5]==0x00f00140);
    CHECK(psx_mod_read_half(0x8004b818)==0);
    memcpy(saved,ram,sizeof(ram));writes=0;select_icon();CHECK(writes==0);
    fresh();memcpy(ram,saved,sizeof(ram));writes=0;select_icon();CHECK(writes==0);
    CHECK(R(0x8004b3fc)==0x21d); /* engine queue survives state restoration */
    fresh();legacy_request();CHECK(R(RETURN)==0x249);
    root_close();memcpy(saved,ram,sizeof(ram));transition();
    CHECK(cpu.gpr[4]==0x21d && R(RETURN)==0x21d && R(RETURN+4)==225700 && R(RETURN+8)==164434);
    CHECK(R(PARENT+0x78)==0 && R(ROOT+0xa0)==0);
    writes=0;transition();CHECK(writes==0); /* consumed once */
    memcpy(ram,saved,sizeof(ram));transition();CHECK(R(RETURN)==0x21d); /* pending savestate */
    fresh();legacy_request();root_close();enabled=0;transition();CHECK(R(RETURN)==0x249 && R(PARENT+0x78)==0);
    fresh();legacy_request();root_close();watching=0;W(0x8004b370,0x15);watching=1;transition();CHECK(R(RETURN)==0x249);
    fresh();legacy_request();watching=0;W(PARENT+0x24,0x1f801000);watching=1;writes=0;
    cpu.gpr[31]=0x800997ec;cpu.gpr[16]=PARENT;shinka_map_frame(&cpu);CHECK(writes==0);
    /* Every exposed icon must lead to its own area according to the original map. */
    {
        const unsigned icons[]={20,30,22,21,15,26};
        for(unsigned i=0;i<6;++i) {
            fresh();watching=0;W(RETURN,0x200);W(MAP+0x184,icons[i]);W(MAP+0xa8+(icons[i]-1)*4,1);watching=1;
            select_icon();shinka_map_present();CHECK(R(0x8004b3fc)==R(RETURN));
            CHECK(R(RETURN)!=0x200 && map_stage_icons[R(RETURN)-0x200]+1==icons[i]);
        }
    }
    for(unsigned rejection=0;rejection<6;++rejection) {
        fresh();select_icon();watching=0;
        switch(rejection) {
        case 0:enabled=0;break;
        case 1:W(0x8004b370,0x15);break;
        case 2:W(RETURN,0x200);break;
        case 3:memset(ptr(0x8004b3c0),0,30);break;
        case 4:W(0x8004de5c,0);break; /* never clear an unfamiliar VRAM layout */
        case 5:W(0x8004b3fc,0xd00);break;
        }
        watching=1;shinka_map_present();
        CHECK(gpu_count==0 && R(RETURN)!=(uint32_t)0x21d);
        CHECK(R(0x8004b3fc)==(rejection==5 ? 0xd00u : 0));
    }
    for(unsigned rejection=0;rejection<15;++rejection) {
        fresh();watching=0;
        switch(rejection) {
        case 0:enabled=0;break;
        case 1:W(PARENT+0x20,2);break; /* legacy controller allocation */
        case 2:W(MAP+0x180,0);break; /* free cursor, stale selected index */
        case 3:W(MAP+0x184,47);break;
        case 4:W(RETURN,0x20d);break; /* interior */
        case 5:W(RETURN,0x2b3);break; /* other server */
        case 6:W(0x8004b370,0x25);break; /* unvalidated late campaign */
        case 7:memset(ptr(0x8004b3c0),0,30);break; /* map icon alone isn't visitation */
        case 8:W(0x80098294,0);break; /* unknown overlay */
        case 9:psx_mod_write_half(0x8004b818,(1<<13)|(1<<4));break;
        case 10:W(0x8004b3fc,0xd00);break; /* another transition already queued */
        case 11:W(MAP+0x78,1);break; /* Amaterasu map */
        case 12:W(MAP+0xa8+29*4,0);break; /* hidden icon */
        case 13:psx_mod_write_half(0x8004b818,(1<<13)|(1<<14));break;
        case 14:W(MAP+0x184,14);W(MAP+0xa8+13*4,1);break; /* unvalidated arrival */
        }
        watching=1;writes=0;select_icon();CHECK(writes==0 && R(PARENT+0x78)==0);
    }
    fresh();watching=0;W(MAP+0x184,26);W(MAP+0xa8+25*4,1);watching=1;writes=0;
    select_icon();CHECK(writes==0); /* same location */
    fresh();watching=0;W(0x801e0000,47);W(0x801e0004+30*4,200);
    psx_mod_write_byte(0x801e00c8,14);psx_mod_write_byte(0x801e00c9,0);watching=1;
    cpu.gpr[31]=0x8009843c;cpu.gpr[16]=MAP;cpu.gpr[5]=0x801e0000;cpu.gpr[6]=30;
    shinka_map_text(&cpu);CHECK(cpu.gpr[6]==0xffffffff && psx_mod_read_byte(cpu.gpr[5]+1)==2);
    CHECK(psx_mod_read_byte(cpu.gpr[5]+2)==1); /* name retained, hint on next line */
    watching=0;
    psx_mod_write_byte(0x801e00c9,2);psx_mod_write_byte(0x801e00ca,1);
    psx_mod_write_byte(0x801e00cb,15);psx_mod_write_byte(0x801e00cc,0);watching=1;
    cpu.gpr[5]=0x801e0000;cpu.gpr[6]=30;shinka_map_text(&cpu);
    CHECK(psx_mod_read_byte(cpu.gpr[5]+4)==13 && psx_mod_read_byte(cpu.gpr[5]+7)==15);
    CHECK(psx_mod_read_byte(cpu.gpr[5]+8)==2); /* two original names share one line */
    puts("Map travel: direct engine queue, visited destinations, legacy pending states, restore and write guards passed.");
    return 0;
}
