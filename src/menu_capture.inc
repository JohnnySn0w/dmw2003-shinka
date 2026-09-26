/* Debug-only, bounded capture of consecutive display frames. No readback or
 * allocation in normal play. Unlike screenshot polling, this cannot miss an
 * intermediate animation frame. The output is SHCAP001 followed by records:
 * eight little-endian u32s (frame,w,h,mode,layout,wide,root,pad), then ARGB pixels. */
#include "menu_wide.h"
static FILE* menu_capture_file;
static unsigned menu_capture_remaining, menu_capture_written;
static int menu_capture_failed;
static size_t menu_capture_bytes;
static void menu_capture_frame(void) {
    if (!menu_capture_file) return;
    GpuDisplayInfo di; gpu_get_display_info(&di);
    int wide = ws_nw_extra() > 0 && gr_wide_supported();
    int scale = wide ? gr_scale() : 1;
    if (scale < 1) scale = 1;
    unsigned w = (di.width + (wide ? ws_nw_extra() : 0)) * scale;
    unsigned h = di.height * scale;
    uint32_t* pixels = NULL;
    if (!di.disabled && w && h && w <= 2048 && h <= 1024) {
        pixels = (uint32_t*)malloc((size_t)w*h*sizeof(*pixels));
        if (pixels && wide) {
            if (gr_render_wide_display(pixels,w*4,di.display_x,di.display_y,di.height) <= 0) {
                free(pixels); pixels = NULL;
            }
        } else if (pixels) {
            /* GPU presentation can leave CPU VRAM stale. Match screenshot_file's
             * explicit readback; never overwrite packed 24-bit movie pixels. */
            if (!di.depth24) {
                extern void gl_renderer_sync_cpu(void);
                extern void vk_renderer_sync_cpu(void);
                gl_renderer_sync_cpu();
                vk_renderer_sync_cpu();
            }
            for (unsigned y=0;y<h;++y) for (unsigned x=0;x<w;++x) {
                uint8_t r,g,b; gpu_display_pixel_rgb(&di,x,y,&r,&g,&b);
                pixels[y*w+x] = 0xff000000u | ((uint32_t)r<<16) | ((uint32_t)g<<8) | b;
            }
        }
    }
    uint32_t header[8] = {(uint32_t)s_frame_count,pixels?w:0,pixels?h:0,
        psx_read_word(0x8004b3f8),shinka_menu_status_layout(),wide,
        shinka_menu_root_active(),sio_get_pad_buttons()};
    size_t bytes = sizeof(header) + (pixels ? (size_t)w*h*4 : 0);
    if (menu_capture_bytes + bytes > 256u*1024u*1024u
        || fwrite(header,sizeof(header),1,menu_capture_file) != 1
        || (pixels && fwrite(pixels,4,(size_t)w*h,menu_capture_file) != (size_t)w*h))
        menu_capture_failed = 1;
    menu_capture_bytes += bytes;
    free(pixels);
    ++menu_capture_written;
    if (!--menu_capture_remaining || menu_capture_failed) {
        if (fclose(menu_capture_file)) menu_capture_failed = 1;
        menu_capture_file = NULL;
    }
}
static void handle_menu_capture(int id,const char* json) {
    int frames=json_get_int(json,"frames",0);
    if (frames) {
        char path[512];
        if (frames<1 || frames>180 || menu_capture_file
            || !json_get_str(json,"path",path,sizeof(path))) {
            send_err(id,"Use 1..180 frames and a path; wait for the current capture to finish");return;
        }
        menu_capture_file=fopen(path,"wb");
        if (!menu_capture_file) {send_err(id,"Cannot open capture path");return;}
        if (fwrite("SHCAP001",1,8,menu_capture_file)!=8) {
            fclose(menu_capture_file);menu_capture_file=NULL;send_err(id,"Cannot write capture header");return;
        }
        menu_capture_remaining=frames;menu_capture_written=0;menu_capture_failed=0;
        menu_capture_bytes=8;
    }
    send_fmt("{\"id\":%d,\"ok\":true,\"active\":%s,\"written\":%u,\"failed\":%d}",
        id,menu_capture_file?"true":"false",menu_capture_written,menu_capture_failed);
}
