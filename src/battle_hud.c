#include "battle_hud.h"
#include "view.h"
#include "mod_plugins.h"

static int active(int margin) {
    return margin>0 && margin<=160 && shinka_view_wide_active()
        && psx_mod_read_word(0x8004b3f8u)==0x600;
}

int shinka_battle_hud_portrait(int left, int top, int right, int bottom, int margin) {
    return active(margin) && left==208+margin && right==307+margin
        && (top==76 || top==332) && bottom==top+59;
}

int shinka_battle_hud_cursor(int sx, int sy, int dx, int dy, int w, int h, int margin) {
    /* Twelve animation tiles occupy the strip immediately below the display. */
    return active(margin) && sx>=0 && sx<=132 && sx%12==0 && sy==244 && w==12 && h==12
        && dx>=0 && dx<=308 && dy>=0 && dy<496 && (dy&255)>=60 && (dy&255)<=224;
}

/* Match the native dialogue's six textured pieces. Stretch only the four
 * middle strips; keep corner artwork and text at their original pixel size.
 * Outer bounds match the health panels: [8,311) before adding wide margins. */
int shinka_battle_dialogue_tile(const uint32_t* words, int count, int offset_x, int offset_y,
    int left, int top, int right, int bottom, int margin, int* x) {
    int native_x, span, index;
    if(count!=4 || !active(margin) || offset_x!=0 || (offset_y!=0 && offset_y!=256)
        || left!=0 || right!=319 || top!=offset_y || bottom!=top+239
        || words[0]>>24!=0x64 || words[1]>>16!=188) return 0;
    native_x=(int16_t)words[1];
    if(native_x==11 && words[2]==0x3e617de0 && words[3]==0x00260008) {
        *x=8-margin; return 8;
    }
    if(native_x==275 && words[2]==0x3e614670 && words[3]==0x00260020) {
        *x=279+margin; return 32;
    }
    if(native_x<19 || native_x>211 || (native_x-19)%64
        || words[2]!=0x3e6120bc || words[3]!=0x00260040) return 0;
    index=(native_x-19)/64;
    span=263+2*margin;
    *x=16-margin+index*span/4;
    return (index+1)*span/4-index*span/4;
}

/* Transform the host's collected command, never the game's packet in RAM.
 * The battle uses a zero-origin 320x240 draw environment for its HUD, a
 * (160,120) origin for the arena, and a separate 100x60 portrait viewport.
 * Preserve each primitive's size/UV and translate every vertex equally. */
void shinka_battle_hud_command(uint32_t* words, int count, int offset_x, int offset_y,
    int left, int top, int right, int bottom, int margin) {
    unsigned op;
    int pos[4], n=0, minx=32767, maxx=-32768, miny=32767, maxy=-32768, dx;
    if (count < 1 || count > 12 || !active(margin)) return;
    op=words[0]>>24;
    /* Move both the portrait's clipping rectangle and its 3D draw origin.
     * Check each native value; incoming packets are always unshifted, including
     * after state loads. Both vertical framebuffer bands use the same layout. */
    if (op==0xe3 && (words[0]&1023)==208
        && (((words[0]>>10)&1023)==76 || ((words[0]>>10)&1023)==332)) {
        words[0]+=margin; return;
    }
    if (op==0xe4 && left==208+margin && (top==76 || top==332)
        && (words[0]&1023)==307 && ((words[0]>>10)&1023)==(unsigned)(top+59)) {
        words[0]+=margin; return;
    }
    if (op==0xe5 && left==208+margin && right==307+margin
        && (top==76 || top==332) && bottom==top+59
        && (words[0]&2047)==258 && ((words[0]>>11)&2047)==(unsigned)(top+30)) {
        words[0]+=margin; return;
    }
    if (offset_x!=0 || (offset_y!=0 && offset_y!=256)
        || left!=0 || right!=319 || top!=offset_y || bottom!=top+239) return;

    if (op>=0x20 && op<=0x3f) {
        int stride=1+!!(op&0x10)+!!(op&4);
        n=(op&8) ? 4 : 3;
        for(int i=0;i<n;++i) pos[i]=1+i*stride;
    } else if (op>=0x40 && op<=0x57 && !(op&8)) {
        n=2;pos[0]=1;pos[1]=(op&0x10) ? 3 : 2;
    } else if (op>=0x60 && op<=0x7f) {
        n=1;pos[0]=1;
    } else return; /* environment, transfers and variable polylines */
    for(int i=0;i<n;++i) {
        int x,y;
        if(pos[i]>=count) return;
        x=(int16_t)words[pos[i]];y=(int16_t)(words[pos[i]]>>16);
        if(x<minx) minx=x;if(x>maxx) maxx=x;
        if(y<miny) miny=y;if(y>maxy) maxy=y;
    }
    if(n==1) {
        int size=(op>>3)&3,w,h;
        if(!size) {
            int index=(op&4) ? 3 : 2;
            if(index>=count) return;
            w=words[index]&65535;h=words[index]>>16;
        } else w=h=size==1 ? 1 : size==2 ? 8 : 16;
        if(w<=0 || h<=0) return;
        maxx+=w;maxy+=h;
    }
    if(minx<0 || maxx>320 || miny<0 || maxy>240) return;
    /* Keep the entire command/submenu layout on the left, including wide Tag
     * bars and DV choices. Only the portrait backdrop belongs to the right in
     * this lower region; its model uses the separate viewport handled above. */
    dx=op==0x66 && minx==206 && miny==74 && maxx==310 && maxy==138 ? margin
        : miny>=74 ? -margin : (miny>=60 && minx<160 && maxx<=164) ? -margin
        : maxx<=160 ? -margin : minx>=160 ? margin : 0;
    if(miny>=188) {
        unsigned clut=op==0x64 ? words[2]>>16 : 0;
        dx=-margin-3;
        /* The technique cost uses its own font CLUT and right-hand footer.
         * Ordinary dialogue, even long second lines, remains left anchored. */
        /* The advance marker pulses through five CLUT rows. Its UV, size and
         * position stay fixed; matching just one palette makes it jump as the
         * other animation frames fall through to the left-text rule. */
        if(op==0x64 && miny==208 && ((minx>=257 && clut==0x3b17)
            || (minx==291 && (words[2]&65535)==0x3c54 && words[3]==0x000c000c
                && clut>=0x3057 && clut<=0x3157 && (clut-0x3057)%0x40==0)))
            dx=margin+4;
    }
    for(int i=0;i<n;++i)
        words[pos[i]]=(words[pos[i]]&0xffff0000u)|(uint16_t)((int16_t)words[pos[i]]+dx);
}
