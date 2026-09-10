/* The cursor normally uses CopyImage to both vertical display bands. A negative
 * VRAM destination would wrap into texture memory. Draw its native 16-bit tile
 * through the renderer facade instead, which understands the wide margin. */
static int shinka_hud_cursor_blit(int sx, int sy, int dx, int dy, int w, int h) {
    int margin=ws_nw_extra()/2, band=dy&256;
    if (!shinka_battle_hud_cursor(sx,sy,dx,dy,w,h,margin)) return 0;
    gr_set_draw_area(0,band,319,band+239);
    gr_set_draw_offset(0,band);
    gr_wide_configure(ws_nw_present_width(),margin);
    gr_wide_set_target(0);
    gr_set_texture_window(0);
    setup_textured_draw(0x808080,0,1);
    gr_draw_textured_rect(dx-margin,dy,w,h,sx,sy,0,0,0x100);
    gr_set_texture_window(texture_window_value);
    gr_set_draw_area(draw_area_left,draw_area_top,draw_area_right,draw_area_bottom);
    gr_set_draw_offset(draw_offset_x,draw_offset_y);
    ws_nw_sync_target();
    return 1;
}
