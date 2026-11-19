/* Draw from the resident font's Cross artwork without writing guest VRAM or
 * reserving atlas space. Horizontal runs keep this bounded to two tiny icons.
 * Both SPRT and animated FT4 paths supply their final transformed rectangle. */
static int shinka_settings_button_draw(int x, int y, int w, int h,
    int u, int v, unsigned clut, unsigned page, uint32_t color24) {
    int direction = shinka_settings_button_direction((unsigned)(u | (v<<8)), clut, page);
    if (direction < 0 || w <= 0 || h <= 0 || w > 16 || h > 24) return 0;
    uint16_t packed[36], palette[16], pixels[144];
    /* Native Cross: page 0x26, UV (232,9), CLUT 0x3817. Font uploads already
     * populate CPU VRAM; no GPU readback or texture allocation is required. */
    for (int row=0; row<12; ++row) for (int col=0; col<3; ++col)
        packed[row*3+col] = vram[(9+row)*1024+442+col];
    for (int i=0; i<16; ++i) palette[i] = vram[224*1024+368+i];
    shinka_settings_button_pixels(packed, palette, direction, pixels);
    x -= w/4; w = w*3/2; /* Centre a 12px badge on the original 8px glyph. */
    for (int row=0; row<12; ++row) {
        int y0=y+row*h/12, y1=y+(row+1)*h/12;
        if (y1 == y0) continue;
        for (int col=0; col<12;) {
            uint16_t pixel=pixels[row*12+col];
            int end=col+1;
            while (end<12 && pixels[row*12+end]==pixel) ++end;
            if (pixel) {
                unsigned r=(pixel&31)*(color24&255)/128;
                unsigned g=((pixel>>5)&31)*((color24>>8)&255)/128;
                unsigned b=((pixel>>10)&31)*((color24>>16)&255)/128;
                uint16_t shade=(uint16_t)((r>31?31:r)|((g>31?31:g)<<5)|((b>31?31:b)<<10));
                int x0=x+col*w/12, x1=x+end*w/12;
                if (x1>x0) gr_draw_flat_rect(x0,y0,x1-x0,y1-y0,shade);
            }
            col=end;
        }
    }
    return 1;
}
