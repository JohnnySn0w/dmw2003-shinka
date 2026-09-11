#include "field_tiles.h"
#include <string.h>

/* Independently decoded field container: three lists of up to five rectangles,
 * followed by an indexed TIM. RLEN wraps the complete container, not each row.
 * No guest pointers or unchecked lengths are accepted by this decoder. */
static unsigned h(const uint8_t* b) { return b[0] | (unsigned)b[1]<<8; }
static uint32_t w(const uint8_t* b) { return h(b) | (uint32_t)h(b+2)<<16; }

int shinka_field_decode(const uint8_t* input, size_t size, ShinkaFieldTile* tile) {
    uint8_t inflated[0xa800];
    const uint8_t* b=input;
    size_t p=4, end;
    unsigned count=0;
    if (!input || !tile || size<16 || size>0xa800) return 0;
    if (w(b)==0x4e454c52) {
        size_t in=8, out=0, expected=w(b+4);
        if (expected<16 || expected>sizeof(inflated)) return 0;
        for (;;) {
            unsigned code,n;
            if (in>=size) return 0;
            code=b[in++];
            if (!code) break;
            n=code&127;
            if (n>expected-out) return 0;
            if (code&128) {
                if (in>=size) return 0;
                memset(inflated+out,b[in++],n);
            } else {
                if (n>size-in) return 0;
                memcpy(inflated+out,b+in,n);in+=n;
            }
            out+=n;
        }
        if (out!=expected) return 0;
        b=inflated;size=out;
    }
    end=w(b);
    if (end<16 || end>size-8) return 0;
    for (unsigned layer=0;layer<3;++layer) {
        unsigned n;
        if (p+4>end) return 0;
        n=w(b+p);p+=4;
        if (n>5 || p+12*n>end) return 0;
        for(unsigned i=0;i<n;++i,p+=12) {
            ShinkaFieldPart part={(int16_t)h(b+p),(int16_t)h(b+p+2),
                (int16_t)h(b+p+4),(int16_t)h(b+p+6),(int16_t)h(b+p+8),
                (int16_t)h(b+p+10),(uint8_t)layer};
            /* Foreground pieces can overlap the next 128-pixel cell by one
             * pixel (e.g. Central Park's wall cap: x=27, width=102). */
            if (part.x<0 || part.y<0 || part.w<=0 || part.h<=0
                || part.x+part.w>129 || part.y+part.h>129
                || part.u<0 || part.v<0) return 0;
            tile->parts[count++]=part;
        }
    }
    if (p!=end || w(b+p)!=16 || w(b+p+4)!=9) return 0;
    p+=8;
    if (size-p<524 || w(b+p)!=524 || h(b+p+8)!=256 || h(b+p+10)!=1) return 0;
    for(unsigned i=0;i<256;++i) tile->palette[i]=(uint16_t)h(b+p+12+i*2);
    p+=524;
    if(size-p<12) return 0;
    unsigned width=h(b+p+8),height=h(b+p+10);
    if(!width || width>128 || !height || height>128
        || w(b+p)!=12+width*height*2 || size-p<12+width*height*2) return 0;
    for(unsigned i=0;i<count;++i)
        if(tile->parts[i].u+tile->parts[i].w>(int)width*2
            || tile->parts[i].v+tile->parts[i].h>(int)height) return 0;
    for(unsigned i=0;i<width*height;++i) tile->pixels[i]=(uint16_t)h(b+p+12+i*2);
    tile->width=width;tile->height=height;tile->count=count;
    return 1;
}
