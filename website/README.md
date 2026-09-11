# Shinka website

A scrolling, responsive feature showcase using the user's full title artwork,
real gameplay captures, opt-in feature GIFs and a continuous audible recording
of Original → DS → Sampled → Chip switching in Central Park.

## Preview locally

From this directory, serve the static output with Python:

```sh
python -m http.server 4173 --bind 127.0.0.1 --directory dist
```

Open <http://127.0.0.1:4173/>. No package install or build step is required.
The HTML, CSS and JavaScript in `dist/` are the authored source. Relative asset
paths also allow hosting under a repository subdirectory.

## Editing and publishing

- Edit `dist/index.html`, `dist/style.css` and `dist/app.js`.
- Keep performance claims tied to the linked measurement reports.
- Keep recordings small and retain their provenance in [MEDIA.md](MEDIA.md).
- Audio begins only through a user gesture. GIFs start as still images and have
  explicit play/stop controls; they do not autoplay.
- `.openai/hosting.json` identifies the existing private Sites project and static
  output. It contains no credentials. Reuse that project for future Sites edits.
- The game repository tracks this website as ordinary files. A local nested Git
  checkout used by Sites contains only this folder and is not a submodule.

No disc images, BIOS, generated game code, memory cards or complete soundtrack
packs are deployed. See the root [data policy](../README.md#data-and-assets).
