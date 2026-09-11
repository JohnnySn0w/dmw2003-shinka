/* Included in the local renderer copy before gl_swap_with_osd. Resources are
 * uploaded once, on its owning GL context. Guest VRAM never contains this PNG. */
static GLuint shinka_title_tex, shinka_title_prog;
static int shinka_title_attempted, shinka_title_w, shinka_title_h;
static GLint shinka_title_uv, shinka_title_alpha;

static void shinka_title_gl_reset(void) {
    shinka_title_ready(0);
    if (shinka_title_tex) glDeleteTextures(1, &shinka_title_tex);
    /* The immediately following context destruction releases the program,
     * matching the pinned renderer's other shader-program lifetimes. */
    shinka_title_tex = shinka_title_prog = 0;
    shinka_title_attempted = 0;
}

static void shinka_title_gl_draw(int ww, int wh) {
    float alpha;
    int lx, ly, lw, lh, dw, dh, x, y;
    if (!shinka_title_attempted) {
        unsigned char *pixels;
        shinka_title_attempted = 1;
        pixels = shinka_title_load(&shinka_title_w, &shinka_title_h);
        if (!pixels) return;
        shinka_title_prog = build_program(PRESENT_VS,
            "#version 330\n"
            "in vec2 v_uv; uniform sampler2D u_tex; uniform float u_alpha; out vec4 frag;\n"
            "void main(){ frag=texture(u_tex,v_uv); frag.a*=u_alpha; }\n");
        if (shinka_title_prog) {
            glGenTextures(1, &shinka_title_tex);
            p_glActiveTexture(PSXGL_TEXTURE0);
            glBindTexture(GL_TEXTURE_2D, shinka_title_tex);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, shinka_title_w, shinka_title_h,
                         0, GL_RGBA, GL_UNSIGNED_BYTE, pixels);
            p_glUseProgram(shinka_title_prog);
            p_glUniform1i(p_glGetUniformLocation(shinka_title_prog, "u_tex"), 0);
            shinka_title_uv = p_glGetUniformLocation(shinka_title_prog, "u_uv_rect");
            shinka_title_alpha = p_glGetUniformLocation(shinka_title_prog, "u_alpha");
            p_glUseProgram(0);
            shinka_title_ready(shinka_title_tex != 0);
        }
        shinka_title_free(pixels);
    }
    alpha = shinka_title_opacity();
    if (!shinka_title_tex || alpha <= 0.0f) return;
    letterbox_rect_aspect(ww, wh, 4, 3, &lx, &ly, &lw, &lh);
    dw = lw * 220 / 320;
    dh = dw * shinka_title_h / shinka_title_w;
    x = lx + (lw - dw) / 2;
    y = ly + lh * 8 / 240;
    p_glBindFramebuffer(PSXGL_DRAW_FRAMEBUFFER, 0);
    glViewport(x, wh - y - dh, dw, dh);
    glDisable(GL_SCISSOR_TEST);
    glDisable(GL_STENCIL_TEST);
    glDisable(GL_DEPTH_TEST);
    glEnable(GL_BLEND);
    p_glBlendEquationSeparate(PSXGL_FUNC_ADD, PSXGL_FUNC_ADD);
    p_glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
    p_glActiveTexture(PSXGL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, shinka_title_tex);
    p_glUseProgram(shinka_title_prog);
    p_glUniform4f(shinka_title_uv, 0.f, 0.f, 1.f, 1.f);
    p_glUniform1f(shinka_title_alpha, alpha);
    p_glBindVertexArray(s_present_vao);
    glDrawArrays(GL_TRIANGLES, 0, 3);
    p_glBindVertexArray(0);
    p_glUseProgram(0);
    glDisable(GL_BLEND);
}
