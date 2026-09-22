# Listening arrangements from instrument labels

The September 21 notebook snapshot has 19 fully labeled music sequences and
seven short sequences labeled as sound effects. The local audition set contains
57 full mixes (Sampled, DS, Chip) and 537 aligned instrument stems. Reliability
Spot is only partly labeled and is excluded. These are first-pass arrangements
of the existing melodies, not newly composed songs or changes to the live pack.

The local set is `output/labelled-arrangements-01/listening/`. Start its listening
page without interrupting the instrument-label notebook:

```powershell
python tools/serve_music_arrangements.py output/labelled-arrangements-01/listening
```

Open <http://127.0.0.1:62007/>. Choose a full mix or expand a track's instrument
choices to open an individual stem. Full mixes are WAV; MP3 listening copies are
also included in `Shinka-labeled-listening-samples.zip`. Stems are lossless FLAC,
with identical start times. Only one browser audio player plays at a time.

## What the labels control

The renderer matches labels by bank, sequence, original source hashes, programs
and sample families. It requires every family in a sequence to be labeled. A
snapshot of the labels and their confidence/notes accompanies the output; the
notebook itself is never rewritten. A tentative label remains tentative.

Sampled uses an expanded CC0 instrument collection: orchestral winds, brass,
strings, pizzicato, harp, mallets, percussion, harpsichord, zither, accordion,
guitars and the earlier piano/bass/clarinet banks. Some choices remain deliberate
substitutes: psaltery for santur, Vietnamese zither for kanun/sitar, strumstick for
banjo/oud, and flute for ney. Timpani, metal-drum, organ and some unusual synth
parts use procedural approximations. These are not claims that those instruments
are acoustically interchangeable. Each part lists the exact recording or
procedural source in `arrangement.json`.

The DS version uses the same arrangement with 32,768 Hz resampling, 12-bit sample
quantization, a 12 kHz mix filter and subtle early reflections. This is a bright
handheld-inspired treatment, not DS hardware emulation or the older Asuka-only
8 kHz preview. Chip uses generated pitched and noise voices. Parts explicitly
labeled SFX stay original in all three versions; standalone SFX cues are copied
separately as unchanged offline auditions.

## Mix and playback limits

- Original sequence note times, note velocities, supported volume/expression,
  panning and pitch bend are retained. Playback is one linear sequence pass with
  a two-second release tail. Custom PS1 loop/reverb/modulation controls are not
  reproduced; unsupported controls are recorded per part.
- Source stems provide relative RMS targets. Percussion gets a 4 dB reduction
  and bass 2.5 dB. One common gain applies to all three mixes and their stems;
  there is no separate boost for each palette. Peaks stay below 0.89 full scale.
- Kit sub-instrument routing is provisional: common MIDI-like key positions
  select kick/snare/hat/cymbal/tom. A family label such as “drum kit” does not
  identify every source drum. The Indian-kit suggestion uses bongo/cajon as an
  explicit placeholder, not an authentic tabla arrangement.
- Named samples use a compact set of pitch zones. Octave conventions were checked
  against sampled pitch; harp, solo pizzicato, xylophone and FM-piano names use
  different conventions from several other library sections. Articulation,
  room sound and sustained loops still need listening feedback.
- Descriptions such as “wet,” “funky,” or instrument comparisons are retained
  as arrangement notes. They are not all implemented as bespoke effects yet.

Validation checks every mix for headroom and every stem for non-silence and
matching length. Summed stems reproduce each mix within 16-bit rounding error.
FLAC packaging compares decoded PCM byte-for-byte before replacing generated
stem WAVs. This does not establish perceptual fidelity; these files are for
listening and revising before any live-pack replacement.

## Rebuild from a completed notebook

Install `tools/requirements-music.txt`, FFmpeg and 7-Zip. Produce the owned
[music exports](music.md) and [split notebook library](music-listening-guide.md)
first. Then, from the repository root:

```powershell
python tools/music_fetch_banks.py
python tools/fetch_labelled_instruments.py --output output/labelled-instruments
python tools/arrange_labelled_music.py --instruments output/labelled-instruments --output output/my-arrangements
python tools/package_music_arrangements.py output/my-arrangements
python tools/serve_music_arrangements.py output/my-arrangements
```

Use a new output folder for each render. `--labels`, `--library` and `--exports`
override the default local paths. Repeat `--track BANK-NNN` for a smaller pass.
New instrument names must receive a reviewed route; they never silently become
piano. The route table lives in `tools/arrange_labelled_music.py` and does not
modify `assets/music/live-routing.json`.

Sample URLs, pinned revisions, hashes and root keys are in
`assets/music/labelled-audition-samples.json`. Downloads are verified before use.
Archive extraction reads only individually pinned members, never arbitrary
archive paths. The input recordings are CC0 from
[VSCO 2 Community Edition](https://github.com/sgossner/VSCO-2-CE),
[Versilian Community Sample Library](https://github.com/sgossner/VCSL), and
[FreePats](https://freepats.zenvoid.org/). Library authors and recordings retain
their source attribution in the catalog and downloaded notices. Original game
music, personal labels and rendered arrangements stay in ignored local output.
