#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "dev_nav.h"
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"line %d: %s\n",__LINE__,#x);exit(1); } } while(0)
static uint8_t ram[0x200000],before[0x200000];
static uint32_t addresses[64];
static unsigned writes;
static unsigned offset(uint32_t a) { CHECK(a>=0x80000000 && a<0x80200000);return a-0x80000000; }
uint32_t psx_read_word(uint32_t a) { uint32_t v;memcpy(&v,ram+offset(a),4);return v; }
uint8_t psx_read_byte(uint32_t a) { return ram[offset(a)]; }
void psx_write_word(uint32_t a,uint32_t v) { CHECK(writes<64);addresses[writes++]=a;memcpy(ram+offset(a),&v,4); }
void psx_write_byte(uint32_t a,uint8_t v) { CHECK(writes<64);addresses[writes++]=a;ram[offset(a)]=v; }
#define R psx_read_word
#define W psx_write_word
static void fresh(void) {
    writes=0;memset(ram,0,sizeof(ram));
    W(0x8004b3f8,0x21d);W(0x8005ccbc,0x800b0000);
    W(0x800b0028,0x80014274);W(0x800b0048,0x80020b58);W(0x800b0020,1);
    W(0x80048d68,0x21d);W(0x8004b370,20);
    W(0x80017b4c,0x00041140);W(0x80017b60,0x3c038005);W(0x80017b64,0x2463949c);
    W(0x800494b8,10);W(0x800494bc,(400u<<16)|23);W(0x800494c0,(200u<<16)|17);
    W(0x800494c4,(55u<<16)|42);
    writes=0;memcpy(before,ram,sizeof(ram));
}
static void unchanged(void) { CHECK(writes==0 && !memcmp(before,ram,sizeof(ram))); }
int main(void) {
    ShinkaNavPartner p;
    for(unsigned source=0x23b;source<=0x23e;source+=3) {
        unsigned destination=source==0x23b?0x23e:0x23b;
        fresh();W(0x8004b3f8,source);writes=0;
        CHECK(!shinka_nav_enter(destination,source));
        CHECK(writes==2 && addresses[1]==0x8004b3fc && R(0x8004b3fc)==destination);
        CHECK(R(0x80048d68)==0x21d && R(0x8004b370)==20);
    }
    fresh();CHECK(shinka_nav_enter(0x23e,0x21d));unchanged();
    fresh();W(0x8004b3f8,0x1000);writes=0;memcpy(before,ram,sizeof(ram));
    CHECK(shinka_nav_enter(0x23e,0x1000));unchanged();
    fresh();W(0x8004b3f8,0x23b);writes=0;memcpy(before,ram,sizeof(ram));
    CHECK(shinka_nav_enter(0x23b,0x23b));CHECK(shinka_nav_enter(0x23e,0x23e));unchanged();
    W(0x8004b3fc,0x600);writes=0;memcpy(before,ram,sizeof(ram));
    CHECK(shinka_nav_enter(0x23e,0x23b));unchanged();
    {
        ShinkaNavLab lab;
        fresh();CHECK(shinka_nav_lab(&lab));unchanged();
        W(0x8004b3f8,0xd01);W(0x80055d28,13);W(0x8008ed0c,0x27bdff40);
        W(0x800b0024,0x800b0100);W(0x800b0100,0x800b1000);
        W(0x800b1028,0x80014274);W(0x800b1048,0x80082f48);W(0x800b1020,1);
        W(0x800b1024,0x800b1100);W(0x800b1100,0x800c0000);
        W(0x800c0028,0x80014274);W(0x800c0048,0x8008ed0c);W(0x800c0020,3);
        W(0x800c000c,1);W(0x800c0064,2);
        W(0x80048da4,1);W(0x80048da8,5);W(0x80048dac,7);
        W(0x800c0024,0x800c0100);W(0x800c0100,0x800d0000);
        W(0x800d0028,0x80014274);W(0x800d0048,0x8008a51c);W(0x800d0020,19);
        W(0x800d0010,3);W(0x800d0060,2);
        writes=0;memcpy(before,ram,sizeof(ram));
        CHECK(!shinka_nav_lab(&lab));CHECK(lab.slot==2 && lab.roster[2]==7);
        CHECK(lab.action_menu==0x800d0000 && lab.action==2);unchanged();
        W(0x800c0024,0xffffffff);writes=0;memcpy(before,ram,sizeof(ram));
        CHECK(!shinka_nav_lab(&lab) && !lab.action_menu);unchanged();
        W(0x800b0024,0xffffffff);writes=0;memcpy(before,ram,sizeof(ram));
        CHECK(shinka_nav_lab(&lab));unchanged();
    }
    fresh();W(0x8004b3f8,0x1000);writes=0;CHECK(!shinka_nav_warp(0x234,111,222,3,0x1000));
    CHECK(writes==6 && addresses[5]==0x8004b3fc);
    CHECK(R(0x8004b3fc)==0x234 && R(0x80048d6c)==111 && R(0x80048d74)==3);
    CHECK(R(0x8004b3f8)==0x1000 && R(0x8004b370)==20);
    fresh();CHECK(shinka_nav_warp(0x234,111,222,3,0x21d));unchanged();
    fresh();W(0x8004b3f8,0x1000);writes=0;memcpy(before,ram,sizeof(ram));
    CHECK(shinka_nav_warp(0x600,1,2,0,0x1000));unchanged();
    CHECK(shinka_nav_warp(0x234,-1,2,0,0x1000));unchanged();
    CHECK(shinka_nav_warp(0x234,1,2,8,0x1000));unchanged();
    CHECK(shinka_nav_warp(0x234,1,2,0,0x202));unchanged();
    fresh();W(0x8004b3fc,0x600);writes=0;memcpy(before,ram,sizeof(ram));
    CHECK(shinka_nav_warp(0x234,1,2,0,0x21d));unchanged();
    fresh();W(0x8004b3f8,0x600);writes=0;memcpy(before,ram,sizeof(ram));
    CHECK(shinka_nav_heal(0,0x600));CHECK(shinka_nav_story(6,0x600));unchanged();
    fresh();W(0x8004b3f8,0x1000);writes=0;
    CHECK(!shinka_nav_warp(0x234,1,2,0,0x1000));
    fresh();CHECK(shinka_nav_flag(0x4000,1,0x21d));unchanged();
    W(0x8004b3e0,0xa5a5a5a5);writes=0;
    CHECK(!shinka_nav_flag(0x4011,1,0x21d));CHECK(R(0x8004b3e0)==0xa5a5a5a7 && writes==1);
    fresh();CHECK(shinka_nav_flag(0x1c50,1,0x21d));
    CHECK(shinka_nav_flag(0x1c51,2,0x21d));unchanged();
    W(0x8004b3bc,0xa5a5a5a5);writes=0;
    CHECK(!shinka_nav_flag(0x1c51,1,0x21d));
    CHECK(writes==1 && addresses[0]==0x8004b3bf && R(0x8004b3bc)==0xa7a5a5a5);
    CHECK(!shinka_nav_flag(0x1c51,0,0x21d));
    CHECK(writes==2 && addresses[1]==0x8004b3bf && R(0x8004b3bc)==0xa5a5a5a5);
    fresh();CHECK(shinka_nav_flag(0x1c51,1,0x202));unchanged();
    W(0x8004b3fc,0x23b);writes=0;memcpy(before,ram,sizeof(ram));
    CHECK(shinka_nav_flag(0x1c51,0,0x21d));unchanged();
    fresh();CHECK(!shinka_nav_heal(0,0x21d));CHECK(writes==2);
    shinka_nav_partner(0,&p);CHECK(p.hp==400 && p.mp==200 && p.strength==42);
    CHECK(R(0x800494c4)==((55u<<16)|42));
    CHECK(!shinka_nav_power(0,999,0x21d));CHECK(R(0x800494c4)==((55u<<16)|999));
    fresh();CHECK(shinka_nav_heal(8,0x21d));CHECK(shinka_nav_heal(1,0x21d));
    CHECK(shinka_nav_power(0,1000,0x21d));unchanged();
    W(0x80017b64,0);writes=0;memcpy(before,ram,sizeof(ram));CHECK(shinka_nav_heal(0,0x21d));unchanged();
    fresh();W(0x80042b1c,0x53480121);writes=0;
    CHECK(!shinka_nav_encounters(0,0x21d));CHECK(R(0x80048d64)==0x100000);
    CHECK(R(0x80042b1c)==0x53480121 && writes==1);
    CHECK(!shinka_nav_encounters(1,0x21d));CHECK(R(0x80048d64)==0);
    puts("developer navigation checks passed");return 0;
}
