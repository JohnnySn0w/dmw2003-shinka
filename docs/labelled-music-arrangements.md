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

## Balance auditions and the mix desk

The next local pass contains a separate set of 57 balanced mixes and 537 aligned
stems under `listening/balanced/`. Open
<http://127.0.0.1:62007/mixer#BGM018-000/sampled> for Badlands. The original
collection and its ZIP remain available; the live game pack is unchanged.
The mix desk also links a ZIP of all 57 balanced MP3 previews, before personal
slider adjustments.

Each track offers approximately level-matched **First mix / Balanced** previews,
then an interactive mix with per-part **Volume**, **Warmth** (300 Hz) and
**Presence** (2.5 kHz). Solo isolates a part for listening. All parts start on the
same audio clock. Manual controls are additional to the automatic corrections,
shown beside each instrument. Reset returns that track/palette to its automatic
balance. Changing a slider saves locally to `listening/mix-adjustments.json`;
settings are separate for Sampled, DS and Chip. A visible error replaces the saved
message if persistence fails. Conflicting edits from another tab require reload.

**Download my mix** renders the current controls to stereo 48 kHz PCM16 WAV in
the browser. It includes all parts, regardless of solo, and attenuates the entire
mix if a sample peak would exceed 0.79. The live preview has a safety compressor
for large boosts; the downloaded WAV uses only a common gain reduction. This
export is a local audition, not an installation into the game.

### What the balancing pass measures

- Compare corresponding active phrases, rather than averaging each stem's
  silences into its level. Reference activity is detected in 400 ms Hann windows,
  200 ms apart, using a relative −35 dB threshold and an absolute floor.
- Use the frequency response of the two 48 kHz filters in
  [ITU-R BS.1770-4](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-4-201510-S!!PDF-E.pdf)
  to weight spectral power. This **windowed loudness proxy is not LUFS**: it does
  not implement the standard's time-domain filtering, block overlap or gates.
  A steady-tone test compares it with the actual filter cascade.
- Match each part against its own original-sample reference, retaining the
  reference's relative hierarchy. Gain corrections are limited to ±6 dB. This
  replaces the first pass's RMS targets and blanket drum/bass cuts; percussion
  can rise or fall if the reference suggests it. The manual controls let the
  listener keep or reject that suggestion.
- Nudge broad warmth/presence energy toward the reference with two Q=0.7 peaking
  filters. Only a quarter of the measured band-ratio difference is applied,
  capped at ±2 dB (±1 dB for drums, triangles and bells). Bands below −35 dB of
  the stem's total power are not boosted. Original SFX parts receive no such
  correction. This avoids prescribing a universal EQ curve for unlike voices.
- Apply a common gain to each finished mix and its stems, targeting −20 on the
  proxy while retaining sample headroom. Transient-heavy tracks may remain
  quieter. No automatic compressor, limiter or masking notch is baked into
  these baseline files. Sample peaks are checked; this is not a true-peak or
  streaming-delivery certification.

The reference is an **offline original-sample approximation**, not a native SPU
recording. Frequency envelopes also change legitimately with register,
articulation and replacement instrument. These bounded suggestions need listening
approval; they cannot infer every melody/accompaniment role or resolve masking
reliably on their own. `balanced/catalog.json` records every correction,
measurement, source identity and comparison trim.

After packaging a fresh arrangement set, build its balance pass and serve it:

```powershell
python tools/balance_music_arrangements.py output/my-arrangements
python tools/serve_music_arrangements.py output/my-arrangements
```

Use `--library` for a different original-stem library or repeat `--track` for a
smaller first pass. Existing completed balance catalogs are preserved: use a new
arrangement folder for a new pass. The profile is tied to the balance catalog's
hash; the server refuses to apply saved settings to a different render. The
server binds only to loopback and protects writes with Host, Origin, per-process
token and revision checks. No labels or audio are sent to an external service.

### September 25 listening checkpoint — balancing paused

The listener reports that the automatic pass sounds fairly minimal, and that
Asuka City's foreground trumpet-like phrase remains recessed. Keep this as
unfinished mix work; the validated files and working mix desk are auditions,
not an approved master or an update to the live game soundtrack.

Inspection of `BGM001-000` found no trumpet voice in the arrangement: the saved
assignments include tuba, clarinet and tentative violins. Which source part
contains the reported phrase has not yet been established. Do not relabel the
notebook or substitute a trumpet based on this observation alone.

The Sampled balance pass raised the main drums by 3.669 dB and tuba by 0.838 dB,
moving their relative balance toward percussion. The replacement tuba's
1.5–5 kHz energy fraction was roughly 23 dB below its reference's; the weak-band
guard therefore applied no presence boost. Matching weighted energy over a
whole part cannot establish melodic prominence or whether accompaniment masks
a phrase. Tentative labels and changed attack/sustain also need review.

Next music work: isolate the reported lead phrase against the original, verify
its instrument and articulation, then compare its level with accompaniment
during that phrase. Reconsider the weak-band guard and restored percussion
levels using listening evidence rather than increasing global EQ. Preserve
existing comparisons and personal mix adjustments. Work moved to the area-entry
widescreen card at the user's request.

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
