# Shinka title screen

The OpenGL presentation layer replaces the European game's title logo with
`assets/branding/shinka-title.png`. This is a cropped, resized RGBA derivative
of the user's stacked SHINKA artwork. Its transparent edges and soft shadow
remain intact. The original background, menu choices and credits remain.

CMake stages the image as `assets/shinka-title.png` beside the executable.
Restart after replacing the image; it is decoded and uploaded once per GL
context. Set `SHINKA_TITLE_LOGO=0` before launching to restore the original
logo. A missing/unreadable image, failed shader setup or non-OpenGL renderer
also leaves the original logo in place.

## Implementation

`tools/title_logo.cmake` extends the generated local GPU/renderer copies;
the pinned framework and disc data are not modified. The command filter in
`src/title_logo.c` recognizes 32 title sprites and ten original shadow sprites
by complete rectangle, UV/CLUT and texture-page identity. It also checks the
scene mode, resident module and native drawing environment, including both
frame buffers. Background and menu palettes are not removed.

`src/title_logo_gl.inc` draws the PNG over the 4:3 title viewport before the
runtime OSD. It follows native logo modulation and observes the outgoing fade
triangles to fade the replacement. The fade is a uniform alpha approximation
of the original subtractive Gouraud effect. The title scene's outgoing owner
modes remain eligible only while its module is resident, avoiding a flash of
the original logo during the handoff.

The image stays at host resolution rather than being quantized into PSX VRAM.
Use the debug `present_shot` command to capture it; raw guest-framebuffer
screenshots do not include this layer.

## Validation — 2026-09-10

- Windows Release build succeeded; all twelve configured Shinka native tests
  passed, including the new `title_logo` guards/fade/lifecycle test. The inherited
  framework `example` test has no built executable and was excluded from this run.
- Live captures verified the title prompt, Start/Continue list, outgoing fade,
  Continue memory-card screen, registration dialogue, opening movie and return
  from the movie to the title. Tests used an isolated save profile.
- Disabling the layer restored the original title logo and shadow.
- The opening-movie checkpoint still exposes stray pixels outside its picture;
  these also appear with the replacement disabled and are separate from this
  title-screen change. The [movie state restoration fix](movie-coherency.md)
  subsequently resolved this on 2026-09-11.

Local screenshots and command captures are under `output/title-screen/` and
are intentionally not published with game imagery. These checks do not establish
campaign coverage or compatibility with other regional releases.
