# Shinka app icon

`shinka.png` is a cleaned-up, AI-assisted interpretation of the emblem in the user-provided reference screenshot, chosen for this project. It retains the blue-and-white angular mark and surrounding orbit. It is not an original logo designed independently of that reference.

`shinka.ico` packages the artwork at 16, 24, 32, 48, 64, 128 and 256 pixels. Regenerate it on Windows with `tools/build_icon.ps1` (System.Drawing; no external dependencies).

CMake embeds the ICO into the executable and stages the PNG as `assets/psxrecomp.png` beside it, matching the pinned runtime's window-icon lookup. Both copies are required for consistent Explorer, window and taskbar presentation. A running process keeps its existing icon until restarted.
