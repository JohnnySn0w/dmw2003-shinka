# Shinka website

A scrolling feature showcase with the user's title artwork and current gameplay
footage. The September 21 refresh replaces the earlier slideshow GIFs and stale
captures with 16 short videos, including:

- Portable Lab entry, evolution hints and technique selection.
- EXP, encounter and view settings.
- Audible Original / DS / Sampled / Chip switching in Central Park and North Badland W.
- An uninterrupted memory-card load and 100% / 150% / 200% battle pose comparisons.
- Successful map travel and an unsupported destination's explanation.
- Card editing, Card Album, Leomon's gym and the title screen.

The aspect comparison switches among four independently captured 4:3/16:9 pairs:
title, field, battle and Card Album. Gameplay artwork retains its proportions.
Videos have native play/pause, seeking and fullscreen controls; action captions
are available. Playback starts only on user input, and only one demo plays at a
time. Soundtrack chapters and scene choices allow quick listening comparisons.

## Preview and checks

From the repository root:

```sh
python tools/serve_website.py
python tools/check_website.py
python -m unittest discover -s tests -p "test_website*.py" -v
node --check website/dist/app.js
```

Open <http://127.0.0.1:4173/>. There is no install or build step. `dist/index.html`,
`dist/style.css` and `dist/app.js` are the authored source. Relative paths work
under the repository's GitHub Pages subdirectory too.

## Recording and editing

Use `tools/record_showcase.py` against an isolated runtime with a copied save
profile. Never point fixture input at the player's live session. Recipes contain
ordinary button inputs and sample-clock times. The title needs composed output
because its logo is drawn after the guest GPU image; see [MEDIA.md](MEDIA.md).

Keep raw frames, cards and recording manifests under ignored `output/`. Publish
only selected clips, lossless posters and descriptive captions. Record source
revision and capture treatment in MEDIA.md. Bump asset query versions when
changing the CSS or JavaScript. Keep benchmark claims tied to measurement docs;
a new demo is not automatically a new benchmark.

GitHub Pages publishing remains the owner's manual workflow described in
[website-publishing.md](../docs/website-publishing.md). The separate existing
`.openai/hosting.json` private preview configuration is preserved.

[SHOWCASE-PLAN.md](SHOWCASE-PLAN.md) separates this completed refresh from future
recordings. No executable, disc image, BIOS, card or music pack is deployed.
