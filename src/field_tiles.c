#include "field_tiles.h"
#include "mod_plugins.h"
#include "view.h"
#include <string.h>
#include <stdlib.h>
#define R psx_mod_read_word
#define W psx_mod_write_word
#define BANK 2048u
#define PACKETS 96u
#define MAGIC 0x53485446u
typedef struct {
    uint32_t source, cell, file, hash, size;
    uint64_t generation;
    ShinkaFieldTile tile;
} TileCache;
static TileCache cache[30];
static uint64_t serial;
static uint32_t owner, arena;
static int slots[2][PACKETS], source_slot=-1, graphics;
static uint32_t prepared,drawn,missing;
uint32_t shinka_field_stat(unsigned i) { return i==0 ? owner : i==1 ? prepared : i==2 ? drawn : missing; }

static int ram(uint32_t p, uint32_t size) {
    return !(p&3) && p>=0x80000000u && size<=0x200000
        && p<=0x80200000u-size;
}
static int object(uint32_t p, uint32_t callback) {
    return ram(p,0x50) && R(p+0x28)==0x80014274 && R(p+0x48)==callback;
}
static int active(void) {
    uint32_t mode=R(0x8004b3f8);
    return graphics && psx_mod_game_started() && mode>=0x200 && mode<0x300
        && shinka_view_wide_active() && shinka_view_get(2)==1;
}
void shinka_field_graphics_ready(int ready) { graphics=ready; }
void shinka_field_reset(void) {
    memset(cache,0,sizeof(cache));
    for(unsigned b=0;b<2;++b) for(unsigned i=0;i<PACKETS;++i) slots[b][i]=-2;
    owner=0;source_slot=-1;
}
int shinka_field_texture_slot(void) { return source_slot; }
const ShinkaFieldTile* shinka_field_texture(unsigned i, uint64_t* generation) {
    if(i>=30 || !cache[i].generation || !active()) return NULL;
    *generation=cache[i].generation;return &cache[i].tile;
}
void shinka_field_gpu_source(uint32_t source) {
    uint32_t offset=(source&0xffffffu)-(arena&0xffffffu);
    source_slot=-1;
    if(arena && offset<2*BANK && R(arena+2*BANK)==MAGIC) {
        unsigned bank=offset/BANK, index=(offset%BANK)/20;
        source_slot=index<PACKETS && active() ? slots[bank][index] : -2;
    }
}

static uint32_t find_owner(void) {
    uint32_t queue[256],head=0,tail=1,found=0;
    queue[0]=R(0x8005ccbc);
    while(head<tail) {
        uint32_t p=queue[head++],n,t;
        if(!ram(p,0x50) || R(p+0x28)!=0x80014274) continue;
        if(object(p,0x800869c8)) { if(found) return 0;found=p;continue; }
        n=R(p+0x20);t=R(p+0x24);
        if(n>64 || !ram(t,n*4) || n>256-tail) continue;
        for(unsigned i=0;i<n;++i) queue[tail++]=R(t+i*4);
    }
    return found;
}
static const ShinkaFieldTile* get_tile(unsigned index,uint32_t p,uint32_t file,uint32_t cell) {
    uint8_t input[0xa800];
    uint32_t source=R(p+0x68),sectors=R(p+0x64),size,hash=2166136261u;
    TileCache* c=&cache[index];
    if(!sectors || sectors>21 || R(p+0x6c)!=1) return NULL;
    size=sectors*2048;
    if(!ram(source,size)) return NULL;
    for(unsigned i=0;i<size;++i) { input[i]=psx_mod_read_byte(source+i);hash=(hash^input[i])*16777619u; }
    if(c->generation && c->source==source && c->cell==cell && c->file==file
        && c->size==size && c->hash==hash) return &c->tile;
    c->generation=0;
    if(!shinka_field_decode(input,size,&c->tile)) return NULL;
    c->source=source;c->cell=cell;c->file=file;c->size=size;c->hash=hash;
    c->generation=++serial;
    return &c->tile;
}

/* Prepend only missing cells to their original layer buckets. The game's
 * working set, resource requests, twelve VRAM slots and physics are untouched.
 * Enhancement primitives live in a separately allocated, double-buffered DMA
 * arena. Their textures are sampled from private GL textures, never guest VRAM. */
void shinka_field_prepare(void) {
    uint32_t camera,bank,ot,children,file,cols,rows,n=0;
    int x,y,left,right,top,bottom,stock_left,stock_top;
    static const unsigned layers[3]={7,3,11};
    const char* control=getenv("SHINKA_FIELD_TILES");
    drawn=missing=0;
    if(control && !strcmp(control,"0")) return;
    if(!active() || R(0x8004b3fc) || R(0x800862fc)!=0x27bdfea0
        || R(0x80086e30)!=0x27bdffb8 || R(0x800869c8)!=0x27bdffd0) return;
    camera=R(0x8004de78);bank=R(0x8004de44);
    if(bank>1 || !ram(camera,0x164) || R(camera+0x138)!=0x8001dfa8
        || R(camera+0x11c)!=0x8001e064 || R(camera+0x68)!=4) return;
    ot=R(camera+0x5c+bank*4);
    if(!ram(ot,64)) return;
    owner=find_owner(); /* retired tasks can retain a valid callback in RAM */
    if(!ram(owner,0x134) || R(owner+0x20)!=31) return;
    children=R(owner+0x24);cols=R(owner+0x68);rows=R(owner+0x6c);file=R(owner+0x64);
    x=(int32_t)R(camera+0x70)>>8;y=(int32_t)R(camera+0x74)>>8;
    if(!ram(children,124) || cols<1 || cols>256 || rows<1 || rows>256
        || x<0 || y<0 || x>=(int)cols*128 || y>=(int)rows*128
        || R(owner+0x58)!=(uint32_t)x || R(owner+0x5c)!=(uint32_t)y) return;
    if(!arena || R(arena+2*BANK)!=MAGIC) {
        arena=psx_mod_alloc_gpu_dma_memory(2*BANK+4,4);
        if(!arena) return;
        W(arena+2*BANK,MAGIC);
        for(unsigned b=0;b<2;++b) for(unsigned i=0;i<PACKETS;++i) slots[b][i]=-2;
    }
    for(unsigned l=0;l<3;++l) {
        uint32_t offset=(R(ot+layers[l]*4)&0xffffff)-(arena&0xffffff);
        if(offset<2*BANK) return; /* already prepared; never link a cycle */
    }
    for(unsigned i=0;i<PACKETS;++i) slots[bank][i]=-2;
    ++prepared;
    left=x<53 ? 0 : (x-53)/128;right=(x+372)/128;
    top=y/128;bottom=(y+239)/128;
    if(right>=(int)cols) right=(int)cols-1;
    if(bottom>=(int)rows) bottom=(int)rows-1;
    stock_left=x<32 ? 0 : (x-32)/128;stock_top=y<8 ? 0 : (y-8)/128;
    for(int cy=top;cy<=bottom;++cy) for(int cx=left;cx<=right;++cx) {
        uint32_t cell=cy*cols+cx;
        if(cx>=stock_left && cx<stock_left+4 && cy>=stock_top && cy<stock_top+3) continue;
        ++missing;
        for(unsigned i=0;i<30;++i) {
            uint32_t p=R(children+(i+1)*4);
            if(!ram(p,0x254) || !object(p,0x800872e4) || R(p+0x58)!=cell) continue;
            const ShinkaFieldTile* tile=get_tile(i,p,file,cell);
            if(!tile) break;
            for(unsigned j=0;j<tile->count && n<PACKETS;++j) {
                const ShinkaFieldPart* part=&tile->parts[j];
                int sx=cx*128-x+part->x,sy=cy*128-y+part->y;
                uint32_t packet=arena+bank*BANK+n*20,head=ot+layers[part->layer]*4;
                unsigned r=128,g=128,b=128;
                /* Native field modulation, including the foreground tint. */
                if(part->layer==2 || psx_mod_read_byte(0x80099dbb)) {
                    r=psx_mod_read_byte(0x80099db8);g=psx_mod_read_byte(0x80099db9);b=psx_mod_read_byte(0x80099dba);
                }
                if(sx+part->w<=-53 || sx>=373 || sy+part->h<=0 || sy>=240) continue;
                W(packet,0x04000000u|(R(head)&0xffffff));
                W(packet+4,0x64000000u|r|(g<<8)|(b<<16));
                W(packet+8,(uint16_t)sx|((uint32_t)(uint16_t)sy<<16));
                W(packet+12,(uint16_t)part->u|((uint32_t)(uint16_t)part->v<<8));
                W(packet+16,(uint16_t)part->w|((uint32_t)(uint16_t)part->h<<16));
                slots[bank][n++]=(int)i;
                W(head,(R(head)&0xff000000u)|(packet&0xffffff));
            }
            break;
        }
    }
    drawn=n;
}
