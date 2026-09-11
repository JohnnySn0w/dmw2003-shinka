#include "field_tiles.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(c) do { if(!(c)) { fprintf(stderr,"line %d: %s\n",__LINE__,#c);exit(1); } } while(0)
static uint8_t memory[8388608],raw[20480],rle[21000];
static int wide=1,started=1;
static unsigned writes;
static uint32_t next_alloc=0x80600000,latest_alloc;
static unsigned off(uint32_t a) { CHECK((a&0x1fffffff)<sizeof(memory));return a&0x1fffffff; }
uint8_t psx_mod_read_byte(uint32_t a) { return memory[off(a)]; }
uint32_t psx_mod_read_word(uint32_t a) { uint32_t v;memcpy(&v,memory+off(a),4);return v; }
void psx_mod_write_word(uint32_t a,uint32_t v) { memcpy(memory+off(a),&v,4);++writes; }
uint32_t psx_mod_alloc_gpu_dma_memory(uint32_t size,uint32_t align) {
    CHECK(align==4);latest_alloc=next_alloc;next_alloc+=size;return latest_alloc;
}
int psx_mod_game_started(void) { return started; }
int shinka_view_wide_active(void) { return wide; }
int shinka_view_get(int option) { CHECK(option==2);return wide; }
#define W psx_mod_write_word
#define R psx_mod_read_word
static void put(uint8_t* b,unsigned p,uint32_t v) { memcpy(b+p,&v,4); }
static unsigned asset(void) {
    memset(raw,0,sizeof(raw));
    put(raw,0,28);put(raw,4,1);put(raw,16,128|(128u<<16));
    put(raw,28,16);put(raw,32,9);put(raw,36,524);put(raw,44,256|(1u<<16));
    put(raw,48,0x7fffu<<16); /* index zero transparent; index one white */
    put(raw,560,16396);put(raw,568,64|(128u<<16));
    memset(raw+572,1,16384);
    return 16956;
}
static void fixture(void) {
    memset(memory,0,sizeof(memory));shinka_field_reset();
    wide=started=1;shinka_field_graphics_ready(1);
    W(0x8004b3f8,0x21d);W(0x800862fc,0x27bdfea0);
    W(0x80086e30,0x27bdffb8);W(0x800869c8,0x27bdffd0);
    W(0x8005ccbc,0x800a0000);W(0x800a0028,0x80014274);
    W(0x800a0020,1);W(0x800a0024,0x800a1000);W(0x800a1000,0x800e4900);
    W(0x800e4928,0x80014274);W(0x800e4948,0x800869c8);
    W(0x800e4920,31);W(0x800e4924,0x800e4a40);
    W(0x800e4958,288);W(0x800e495c,38);W(0x800e4968,10);W(0x800e496c,10);
    W(0x8004de78,0x800abd40);W(0x800abe78,0x8001dfa8);W(0x800abe5c,0x8001e064);
    W(0x800abd98,0);W(0x800abd9c,0x800b0000);W(0x800abda0,0x800b1000);
    W(0x800abda8,4);W(0x800abdb0,288<<8);W(0x800abdb4,38<<8);
    for(unsigned i=0;i<3;++i) {
        uint32_t p=0x800c0000+i*0x300;
        W(0x800e4a44+i*4,p);W(p+0x28,0x80014274);W(p+0x48,0x800872e4);
        W(p+0x58,i*10+1);W(p+0x68,0x80100000+i*0x5000);W(p+0x64,10);W(p+0x6c,1);
        memcpy(memory+0x100000+i*0x5000,raw,sizeof(raw));
    }
    for(unsigned b=0;b<2;++b) for(unsigned i=0;i<16;++i) W(0x800b0000+b*0x1000+i*4,0xffffff);
}
int main(void) {
    ShinkaFieldTile tile;
    unsigned length=asset(),out=8;
    CHECK(shinka_field_decode(raw,length,&tile));
    CHECK(tile.count==1 && tile.width==64 && tile.height==128 && tile.palette[1]==0x7fff);
    /* Literal RLEN round-trip and all truncations, including a missing terminator. */
    put(rle,0,0x4e454c52);put(rle,4,length);
    for(unsigned i=0;i<length;) { unsigned n=length-i>127 ? 127 : length-i;rle[out++]=(uint8_t)n;memcpy(rle+out,raw+i,n);out+=n;i+=n; }
    rle[out++]=0;
    CHECK(shinka_field_decode(rle,out,&tile));
    for(unsigned n=0;n<out;++n) CHECK(!shinka_field_decode(rle,n,&tile));
    for(unsigned n=0;n<length;++n) CHECK(!shinka_field_decode(raw,n,&tile));
    /* Mixed literal/repeat compression, including runs that cross scanlines. */
    out=8;
    for(unsigned i=0;i<572;) {
        unsigned n=572-i>127 ? 127 : 572-i;
        rle[out++]=(uint8_t)n;memcpy(rle+out,raw+i,n);out+=n;i+=n;
    }
    for(unsigned i=0;i<16384;) {
        unsigned n=16384-i>127 ? 127 : 16384-i;
        rle[out++]=(uint8_t)(128+n);rle[out++]=1;i+=n;
    }
    rle[out++]=0;
    CHECK(shinka_field_decode(rle,out,&tile));
    CHECK(tile.pixels[0]==0x0101 && tile.pixels[8191]==0x0101);
    put(rle,4,length-1);CHECK(!shinka_field_decode(rle,out,&tile));
    put(rle,4,0xa801);CHECK(!shinka_field_decode(rle,out,&tile));
    /* The observed wall-cap geometry reaches x=129; UVs must still fit. */
    put(raw,8,27);put(raw,16,102|(53u<<16));
    CHECK(shinka_field_decode(raw,length,&tile));
    put(raw,8,28);CHECK(!shinka_field_decode(raw,length,&tile));
    put(raw,8,27);put(raw,12,27);CHECK(!shinka_field_decode(raw,length,&tile));asset();
    put(raw,4,6);CHECK(!shinka_field_decode(raw,sizeof(raw),&tile));asset();
    put(raw,32,8);CHECK(!shinka_field_decode(raw,sizeof(raw),&tile));asset();
    put(raw,568,129|(128u<<16));CHECK(!shinka_field_decode(raw,sizeof(raw),&tile));asset();
    fixture();writes=0;shinka_field_prepare();
    CHECK(shinka_field_stat(2)==3 && shinka_field_stat(3)==3 && writes==19);
    uint32_t arena=latest_alloc,head=R(0x800b001c)&0xffffff;
    CHECK(head==(arena&0xffffff)+40);
    CHECK((int16_t)R(arena+8)==-160 && (int16_t)(R(arena+8)>>16)==-38);
    CHECK(R(0x800b000c)==0xffffff && R(0x800b002c)==0xffffff);
    shinka_field_gpu_source((arena&0xffffff)+4);CHECK(shinka_field_texture_slot()==0);
    uint64_t generation;CHECK(shinka_field_texture(0,&generation)!=NULL);
    writes=0;shinka_field_prepare();CHECK(writes==0); /* no duplicate OT links */
    W(0x8004de44,1);shinka_field_prepare();CHECK(shinka_field_stat(2)==3);
    CHECK((R(0x800b101c)&0xffffff)==(arena&0xffffff)+2048+40);
    /* A reused prefetch buffer must refresh its private texture generation. */
    uint64_t previous=generation;
    W(0x80100030,0x12340000);W(0x800b001c,0xffffff);W(0x8004de44,0);
    shinka_field_prepare();
    CHECK(shinka_field_texture(0,&generation)->palette[1]==0x1234 && generation>previous);
    shinka_field_reset();shinka_field_gpu_source((arena&0xffffff)+4);CHECK(shinka_field_texture_slot()==-2);
    CHECK(!shinka_field_texture(0,&generation));
    for(unsigned scenario=0;scenario<5;++scenario) {
        fixture();
        if(scenario==0) wide=0;
        if(scenario==1) W(0x8004b3f8,0x600);
        if(scenario==2) W(0x800862fc,0);
        if(scenario==3) started=0;
        if(scenario==4) shinka_field_graphics_ready(0);
        writes=0;shinka_field_prepare();CHECK(!writes);
    }
    fixture();W(0x800c006c,0);shinka_field_prepare();CHECK(shinka_field_stat(2)==2);
    fixture();W(0x800a0020,0);writes=0;shinka_field_prepare();CHECK(!writes);
    puts("Field container bounds, private tile packets, scene guards and restore behavior passed.");
}
