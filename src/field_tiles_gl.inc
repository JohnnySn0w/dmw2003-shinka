/* Private indexed textures for enhancement-owned edge packets. Keep the
 * original PSX palette, modulation and blend shader; never upload into VRAM. */
static GLuint shinka_field_textures[30];
static uint64_t shinka_field_versions[30];
static void shinka_field_gl_reset(void) {
    if(s_ctx) glDeleteTextures(30,shinka_field_textures);
    memset(shinka_field_textures,0,sizeof(shinka_field_textures));
    memset(shinka_field_versions,0,sizeof(shinka_field_versions));
    shinka_field_raw_texture=0;
    shinka_field_graphics_ready(0);
}
static int shinka_field_gl_rect(int x,int y,int w,int h,int u,int v) {
    uint64_t generation;
    int slot=shinka_field_texture_slot();
    const ShinkaFieldTile* tile;
    shinka_field_graphics_ready(s_raster_ok && !s_cpu_auth_dual);
    if(slot==-1) return 0;
    if(slot<0 || !s_raster_ok || s_cpu_auth_dual) return 1;
    tile=shinka_field_texture((unsigned)slot,&generation);
    if(!tile) return 1;
    flush_flat_batch();flush_tex_batch();flush_cpu_upload();
    if(!shinka_field_textures[slot]) {
        glGenTextures(1,&shinka_field_textures[slot]);
        glBindTexture(GL_TEXTURE_2D,shinka_field_textures[slot]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexImage2D(GL_TEXTURE_2D,0,PSXGL_R16UI,256,256,0,PSXGL_RED_INTEGER,GL_UNSIGNED_SHORT,NULL);
    }
    if(shinka_field_versions[slot]!=generation) {
        glBindTexture(GL_TEXTURE_2D,shinka_field_textures[slot]);
        glPixelStorei(GL_UNPACK_ALIGNMENT,2);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,tile->width,tile->height,
            PSXGL_RED_INTEGER,GL_UNSIGNED_SHORT,tile->pixels);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,128,256,1,
            PSXGL_RED_INTEGER,GL_UNSIGNED_SHORT,tile->palette);
        glPixelStorei(GL_UNPACK_ALIGNMENT,4);
        shinka_field_versions[slot]=generation;
    }
    shinka_field_raw_texture=shinka_field_textures[slot];
    gpu_textured_rect(x,y,w,h,u,v,u+w,v+h,0,128,0x80,s_semi_en?s_semi_mode:-1);
    flush_tex_batch();
    shinka_field_raw_texture=0;
    return 1;
}
