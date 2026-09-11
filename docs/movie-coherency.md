# Movie state restoration and border corruption

## Fix — 2026-09-11

Loading an opening-movie savestate from the title screen could display texture
data in the top and bottom black borders. Fresh attract playback cleared the
borders correctly. The issue reproduced with the Shinka title logo disabled.

The OpenGL renderer maintains GPU and CPU copies of VRAM. Ordinary scenes use
the GPU copy; packed 24-bit movie scanout uses the CPU copy. Entering 24-bit mode
may synchronize pending GPU drawing back into CPU memory. The pinned runtime's
`glb_vram_transfer_in` performed that synchronization **after** writing new CPU
data, including full VRAM restoration from a savestate. The synchronization
overwrote the restored image with the previous scene. Movie uploads then repaired
the picture but never touched its black borders.

`tools/movie_coherency.cmake` moves the depth-transition policy before the CPU
write in the bulk-transfer and point-write paths. This preserves the required
readback of earlier drawing while ensuring the new upload wins. It adds no
readbacks, changes no video dimensions, and neither masks the screen nor alters
save files. Only the generated local renderer is patched; the framework remains
unchanged. Configure-time anchor checks reject incompatible framework revisions.

## Evidence

The original build reproduced corruption when loading a newly saved, clean
movie state from the title screen. Saving and reloading within the movie stayed
clean, isolating the 15-bit-to-24-bit handoff. Captured entry commands also showed
the game clearing VRAM with an opaque black rectangle before fresh playback.
The movie uploads 416 rows starting at row 36 inside a 480-row display.

With the fix, three movie checkpoints loaded from the title screen with clean
borders, and skipping returned to the Shinka title prompt. Nine presented-frame
captures sampled both display buffers; the interior of each top/bottom border
was exactly RGB zero. Windows Release built without warnings or errors. Local
captures and `regression.json` are in `output/movie-borders/`.

This validates the observed opening-movie restoration bug; it is not a claim
that every movie or renderer backend has been tested.
