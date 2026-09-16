#include "cpu_state.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(c) do { if (!(c)) { fprintf(stderr,"line %d: %s\n",__LINE__,#c); exit(1); } } while (0)
static uint32_t ram[0x200000/4], before[0x200000/4];
uint32_t psx_mod_read_word(uint32_t a) { CHECK(!(a&3)); return ram[(a&0x1fffff)/4]; }
void psx_mod_write_word(uint32_t a,uint32_t v) { CHECK(!(a&3)); ram[(a&0x1fffff)/4]=v; }
void shinka_card_progress(CPUState*);
#define W psx_mod_write_word
#define R psx_mod_read_word
static CPUState cpu;
static void setup(int writing) {
    memset(ram,0,sizeof(ram)); memset(&cpu,0,sizeof(cpu));
    cpu.gpr[31]=writing ? 0x8008658c : 0x80085ee8;
    cpu.gpr[6]=0x26c4;cpu.gpr[19]=0x800e7c14;
    W(0x800e7c14+0x48,0x80087534);W(0x800e7c14+0xc,1);
    W(0x800e7c14+0x20,10);W(0x800e7c14+0x10,writing ? 53 : 71);
    W(0x800e7c14+0x24,0x800e8000);W(0x800e8000+28,0x800f9260);
    W(0x800f9260+0x48,0x80083c50);W(0x800f9260+0x28,0x80014274);
    W(0x800f9260+0xc,1);W(0x800f9260+0x10,1);
    W(0x80083c50,0x27bdfef0);W(0x80083d1c,0xae42008c);
    W(0x80048750,writing ? 4 : 3);
}
int main(void) {
    for(int writing=0;writing<2;++writing) {
        setup(writing);
        uint32_t previous=0;
        for(unsigned done=0;done<=0x2700;done+=128) {
            W(0x80048a50,done);
            memcpy(before,ram,sizeof(ram));
            shinka_card_progress(&cpu);
            uint32_t fill=R(0x800f9260+0x8c);
            CHECK(fill>=previous && fill<=0xf33);
            if(!writing && done==0x1380) CHECK(fill==0xf33/2);
            if(writing && done==0x1300) CHECK(fill==0xf33/2);
            if(done==0x2700) CHECK(fill==0xf33);
            previous=fill;
            /* Only presentation state changes, never result/IO/checksum data. */
            before[(0xf9260+0x8c)/4]=fill;
            before[(0xf9260+0x78)/4]=1;
            CHECK(!memcmp(before,ram,sizeof(ram)));
        }
        const uint32_t rejects[][2]={{0x800e7c14+0x48,0},{0x800e7c14+0x10,0},
            {0x800e7c14+0x24,0},{0x800e8000+28,0},{0x800f9260+0x48,0},
            {0x800f9260+0x10,2},{0x800f9260+0xc,3},{0x80048a50,129},
            {0x80048a50,0x2800},{0x80083c50,0},{0x80083d1c,0}};
        for(unsigned i=0;i<sizeof(rejects)/sizeof(*rejects);++i) {
            setup(writing);W(rejects[i][0],rejects[i][1]);
            memcpy(before,ram,sizeof(ram));shinka_card_progress(&cpu);
            CHECK(!memcmp(before,ram,sizeof(ram)));
        }
        setup(writing);cpu.gpr[6]=0xd4;
        memcpy(before,ram,sizeof(ram));shinka_card_progress(&cpu);
        CHECK(!memcmp(before,ram,sizeof(ram)));
        setup(writing);cpu.gpr[31]=0x80010000;
        memcpy(before,ram,sizeof(ram));shinka_card_progress(&cpu);
        CHECK(!memcmp(before,ram,sizeof(ram)));
    }
    return 0;
}
