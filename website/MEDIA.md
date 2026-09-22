# Showcase media provenance

The September 21, 2026 showcase replaces all earlier gameplay demos and stills
with fresh captures of Shinka revision `f3adfad`. Branding remains the user's
artwork. Recordings use an isolated runtime and copied saves under
`output/showcase-20260921/`; the player's active cards and preferences were not
changed. No story flags or visits were added for these recordings.

## Published clips

All clips have native playback controls and load on demand. Audio is present
only in the two soundtrack clips. No clip starts automatically; starting a
second clip pauses the first. The table lists the actual encoded excerpts,
not the older performance measurements quoted on the page.

| Asset in `dist/media/` | Seconds | What it shows |
| --- | ---: | --- |
| `evolution-current.mp4` | 23.04 | Partner selection, locked-form hint, R1/L1 page turns. |
| `settings-current.mp4` | 19.06 | Normal EXP, DV EXP, encounters, screen view and battle motion submenus. Values are demonstrations, not defaults. |
| `card-load.mp4` | 16.06 | Copied memory card: confirm Load, observe the transfer, reach LOADED. No time cuts or turbo. |
| `card-folders.mp4` | 18.12 | Folder highlight pulses, opening the editor and card inspection. |
| `card-album.mp4` | 10.10 | Card selection and page turns. |
| `techniques-current.mp4` | 12.12 | Angemon/Digitamamon stats and the Load Technique list. |
| `title.mp4` | 6.12 | Composed title-screen output including the host-drawn Shinka logo. |
| `sound-central.mp4` | 28.58 | Central Park, Original → DS → Sampled → Chip in one continuous take. |
| `sound-badlands.mp4` | 28.62 | North Badland W, the same four-palette sequence in one continuous take. |
| `map-travel.mp4` | 12.04 | Visited Central Park selected on the map, complete transition, then walking after arrival. |
| `travel-guard.mp4` | 5.12 | East Station shows No travel point yet and refuses Cross. |
| `motion-100.mp4` | 10.06 | Kumamon attack: 100% idle and action pose rate. |
| `motion-150.mp4` | 10.10 | Same saved battle and input schedule: 150% idle and action pose rate. |
| `motion-200.mp4` | 10.08 | Same saved battle and input schedule: 200% idle and action pose rate. |
| `gym-current.mp4` | 10.12 | Leomon training-type selection and return to partner selection; no TP is spent. |
| `portable-lab.mp4` | 12.12 | Field root → DIGIVOLUTIONS → Digivolve → partner actions. |

## Capture treatment

`tools/record_showcase.py` schedules ordinary controller inputs and records
bounded sequences of native display frames. The PAL 50 Hz frame counter retains
elapsed time between chunks; a missing frame at a chunk boundary holds the last
image for that interval. No interval is removed or accelerated. PNG sequences
are encoded as H.264, 852×480, 50 fps, with nearest-neighbor enlargement and
YUV420 chroma subsampling. Encoded 50 fps is not a claim that every frame is unique.
Source frames, inputs, guest state, durations and frame counts stay in the local
recording manifests. Full decode and duration checks are in `media-checks.json`.

The title is the exception: native GPU captures omit its host-drawn logo. Its
clip uses completed `present_shot` readbacks, preserving their sample-clock
spacing (42 captures over 6.12 seconds). Only the black host letterbox is removed
before resizing. The crop is `(0,190)-(2021,1326)`, verified on every wide frame.
The 4:3 title still uses its separately captured full display. Neither title
view is fabricated by cropping the other. Its lower sampling rate is suitable
for this mostly static screen, not an animation timing test.

The two soundtrack clips use the runtime's 44.1 kHz SPU output, with capture-start
alignment within approximately one vblank. Changes occur through the visible
SETTINGS row around 7, 14 and 21 seconds. Captions use the logged input times.
AAC stereo is encoded at 160 kbit/s. There is no post EQ, normalization or
palette-specific recording gain. Both scenes use the current `SHKMUS03` local
pack and runtime mix; routing remains provisional. These are continuous
hot-switch demonstrations, not four repetitions of the same musical phrase.
No full track or music pack is published.

The motion comparison reloads the same battle checkpoint for each rate, uses
Fight at 2 seconds and advances its prompt at 4 seconds. Rates are configured
through the runtime's settings API before recording; whole-game turbo is off.
Idle phase and camera phase may differ slightly during setup. The camera's rate
is not modified; faster pose completion may advance script cues. This is a
visual pace comparison, not a new performance benchmark.

## Stills and aspect comparisons

`album`, `field`, `battle` and `title` each have independently captured
`-original.png` and `-wide.png` views. CSS holds display height constant and
centers the original image with side margins. No wide image is cropped into a
fake 4:3 view. Animated backgrounds and idle poses advance between captures.
Posters are actual frames from their respective clips, saved with lossless PNG
compression. `central-park.png` and `battle.png` are fresh hero captures.

`shinka-title.png` and `emblem.png` preserve the existing supplied branding.
Original game imagery, music and reference-derived artwork retain their
respective rights. The repository contains selected showcase excerpts, not
cards, disc data, generated game code or a soundtrack resource library.
