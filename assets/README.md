# Shinka app icon

`shinka.png` is the authoritative app artwork: the user's improved 909 x 909 RGBA image, with blue strokes and orbit, a white head interior, and transparent background and jaw clearances. It is a reference-derived game motif, not an independently designed logo.

`shinka.svg` retains the earlier manual trace as an editable reference. It does not reproduce the current user-edited PNG. `node tools/render_icon.cjs` renders that earlier trace to `output/icon-touchup/shinka-vector-preview.png` by default (requires `sharp`, resolvable normally or through `NODE_PATH`). The app PNG and ICO are checked in, so ordinary game builds do not require Node or Sharp.

`shinka.ico` packages the artwork at 16, 24, 32, 48, 64, 128 and 256 pixels. Regenerate it on Windows with `tools/build_icon.ps1` (System.Drawing; no external dependencies).

CMake embeds the ICO into the executable and stages the PNG as `assets/psxrecomp.png` beside it, matching the pinned runtime's window-icon lookup. Both copies are required for consistent Explorer, window and taskbar presentation. A running process keeps its existing icon until restarted.

## Pixel-art blue variant

`shinka-pixel-blue.png` isolates the cyan outline and dark blue orbit from the user-supplied purple-background screenshot at its original 386 x 351 resolution. The scene, head interior, eye, and mouth are transparent. Color separation removes the purple fringe; the source pixel shapes and small orbit fragments beside the jaw are retained. This is an optional reference-derived variant; the application continues to use `shinka.png` and `shinka.ico`.
