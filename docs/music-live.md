# Live soundtrack palettes

Open **SETTINGS → Soundtrack** and press Left/Right to select **Original, DS,
Sampled, or Chip**. The saved selection takes effect while a song is playing;
there is no track restart or need to re-enter the area. Switching blends each
active music voice toward its new instrument over roughly 50 ms. New notes use
the selected palette immediately. Normal game fades and reverb remain active.

The current local pack covers **42 exported music banks / 669 sample routes**.
See the [track listening guide](music-listening-guide.md) for scene context.
Unknown banks, environmental sounds, common sound effects, and movie audio keep
their original sound. If the pack is missing, the game continues with original
audio and SETTINGS reports “Music pack missing” for alternate selections.

## What changes

This implementation replaces individual music samples beneath the original
sequencer. The game still chooses notes, pitch, ADSR envelopes, volume, stereo
placement, loop commands, track changes, and battle/digivolution timing. It does
not play an exported MIDI or a looping whole-song WAV beside the emulator.

- **Sampled:** locally generated instrument samples from the five verified CC0
  banks used by the offline auditions.
- **Chip:** generated pulse, triangle, wavetable and percussion samples.
- **DS:** a compact, low-pass-filtered sample/chip blend (70/30 before filtering).
- **Original:** the original decoded ADPCM samples.

The second balance pass raises the melodic source-level ceiling from .22 to
.50 RMS while retaining .80 peak headroom per sample. The old universal ceiling
reduced strong melodic samples much more than quieter percussion. Non-bass
melodic instruments also receive a modest +3 dB presence lift around 2.2 kHz
in the sample domain, before native SPU pitch scaling. DS melodic samples regain
their target level after blending/filtering. Source/target
RMS and achieved palette levels are recorded per route in `music-live.json`.

The next balance pass lowers **percussion by 3 dB and bass by 2 dB** during
playback in DS, Sampled and Chip. Melody levels are unchanged. This uses the
pack's instrument routing rather than note pitch or a filter on the entire
output, so low melody notes and sound effects are not reduced. Gain is applied
before the original SPU envelope, volume and reverb, and before the palette
crossfade. Original audio remains unchanged. This is a shared starting point
for listening review, not a finished mix for every track; provisional routing
can still misclassify an instrument.

These are provisional **sample-level palettes**, not the exact arrangements in
the earlier offline previews. Asuka's sampled/chip choices start from its profile;
Badlands has two guarded sample overrides; remaining routes outside Asuka use
recorded automatic choices that need listening review. A sample
shared by multiple original tones uses the first tone's route. The live DS mix
is a sample/chip blend, whereas the offline DS preview routes whole MIDI parts
between synths. Neither Chip nor DS claims to emulate another sound chip.

Melodic replacements are now rendered around MIDI 60 (bass around MIDI 48),
with a per-route playback ratio compensating the VAB root key and fractional
tuning. Unusually high automatic bass routes use a higher reference to bound
the ratio. The original SPU pitch register still drives the score's note pitch.
Previously, generating a high VAB root and then slowing it down again discarded
upper harmonics. DS's 8 kHz sample filter could also become a 2 kHz cutoff when
a root-84 sample played at note 60. DS now uses a gentler 12 kHz cutoff for
pitched instruments at their reference note; percussion retains its 8 kHz
filter. DS retains its filtered character; Sampled and Chip have no shared
output low-pass filter. Their interpolation remains linear, and individual
instrument routes still need listening review. The existing -3 dB percussion
and -2 dB bass gains are retained. Original
sample stop behavior and ADSR still determine note duration. The generated
sustain loops and source choices are arrangement decisions to refine by ear.
Original panning and mono voice paths are retained; the sampled bank's own
stereo spread is folded to mono before the game's panning and reverb.

## Local build

First export the owned MP/MV pairs with [music_export.py](music.md), install
`tools/requirements-music.txt`, and fetch the pinned banks as described in
[music-palettes.md](music-palettes.md). Keep exported banks in one directory,
with a separate folder per bank containing `music.json` and its sample WAVs.
The builder accepts multiple directories of source MP/MV files:

```powershell
python tools/build_music_live.py --exports output/music-catalog-export --inputs output/music-catalog-audit/inputs --inputs output/music-reference/additional-inputs --output output/music-live
cmake -S . -B build-windows -DSHINKA_MUSIC_PACK="$PWD/output/music-live/music-live.bin"
cmake --build build-windows --config Release --target shinka --parallel 4
```

Substitute your own input paths. The second input directory above is the local
non-BGM export audit's source folder; **the PSF reference download is not a build
input**. The builder checks the MP/MV hashes against each export manifest and
refuses to overwrite its output directory. It writes the binary pack plus a
JSON record of source hashes, routes, and CC0 bank provenance. CMake stages the
pack at `assets/music-live.bin` beside the executable. The current full pack is
about 180 MB; a missing pack does not prevent the game from launching.

New builds use `SHKMUS03`, adding a bounded Q16 playback ratio after each sample's
instrument role. `SHKMUS02` retains role-based gains with its old pitch references;
legacy `SHKMUS01` packs still load at their previous levels. To add only the role
tags without re-rendering an existing pack, use its matching routing report:

```powershell
python tools/upgrade_music_mix.py output/music-live-old/music-live.bin output/music-live-old/music-live.json output/music-live-balanced
```

Then select that new pack with `SHINKA_MUSIC_PACK` and rebuild. The upgrader
checks the source pack hash and binary bounds, preserves PCM, loops and original
bank bytes, and refuses to overwrite an existing output directory. The runtime
applies the role gains; the stored sample RMS measurements remain source levels.
That upgrade produces `SHKMUS02` and cannot recover discarded harmonics. Run
the full builder to regenerate `SHKMUS03` instruments with the new references.

The binary includes owned original bank bytes used for exact identification.
Like the extracted music and generated game code, it is a local build artifact
and must not go in Git or a public release. Source tooling and CC0-bank metadata
are tracked; original samples, reference archives and generated packs are not.

## Isolation and state handling

On note start, the runtime infers a candidate bank's base from the SPU start
address and sample offset, then compares the **entire original bank** against
SPU RAM. A common drum sample alone is insufficient to identify music. Failed
matches pass through unchanged. DMA/PIO uploads revalidate active mappings before
the next render block so reused memory cannot retain an old music instrument.

All three replacement cursors advance alongside the original voice, even when
inaudible. Changing palettes therefore does not retrigger a sustained note. The
audio path performs no disk reads, allocation, or host synthesis. Tables are
loaded on startup, and their parser bounds bank sizes, sample sizes and total
memory. Missing or malformed packs safely fall back to Original.

Savestates retain the original SPU format. Loading one clears host mappings and
re-identifies active notes from restored RAM. Replacement sample phases restart
for already-held notes; subsequent notes, song position and original emulated
timing remain game-driven. Exact alternate-audio phase restoration is not yet
serialized. Original voice capture samples remain canonical; alternate voices
still feed the game's shared output/reverb path. The optional original-ADPCM
shadow renderer is bypassed while alternate palettes are selected.

## Verification

The native regression covers all palette choices, repeated switching, sustained
sample position, loop wrapping, pitch-zero holds, double-rate playback, noise
passthrough, full-bank isolation, upload invalidation, savestate-style mapping
reset, and malformed-pack fallback. Tagged-pack checks cover each role in each
palette, unchanged Original/noise output, loop progression, legacy compatibility
and invalid-role rejection. The Python upgrader tests also check byte-for-byte
preservation of the original banks and replacement waves. It uses synthetic data rather than game
assets. Run `ctest --test-dir build-windows -C Release -R music_live`.

Reference-pitch tests check fractional VAB roots, low/high notes, bounded outliers,
native quarter-rate notes with a fourfold compensation, loop progression,
Original passthrough and malformed-ratio fallback. Existing version-1 and
version-2 fixtures remain covered.

The local headless game check used a copied save profile, the in-game SETTINGS
row, an Asuka-area → Central Park transition, and a random encounter. A battle
checkpoint was then loaded in the final build, all four palettes produced live
audio, and real attack inputs completed the encounter and returned to the field. Captures
of all four palettes had nonzero audio and no clipped samples in the short
comparison windows. This establishes switching, not the musical tastefulness
of all 42 banks or end-to-end listening coverage of the campaign.

The tagged-pack balance pass was also checked live in Central Park and an idle
battle using copied checkpoints: four seconds per palette per scene, all with
matched music notes, nonzero output and no clipped PCM samples. Captures and
levels are local under `output/npc-wide-01/audio-balanced/`. The full upgraded
pack tags 329 melodic, 37 bass and 303 percussion sample routes. These captures
verify playback and switching; they do not establish that every track's mix is
finished. North Badland W and longer battle listening remain useful taste checks.

The reference-pitch revision regenerated all 42 banks / 669 routes from the
verified local exports. Original bank identities and routing assignments were
retained. Four-second field and battle captures in all four palettes had matched
music notes, nonzero output and no clipped samples; these and their peak levels
are in `output/npc-wide-01/audio-reference-final/`. Pitch/filter tests establish
the correction, but whole-track recordings do not isolate melody from drums and
cannot establish subjective tonal balance across the soundtrack.

Developer diagnostics: `{"cmd":"shinka_nav","op":"music"}` returns the saved
palette, pack status and count of matched note starts. Adding `"palette":0..3`
uses the same persistent setter as SETTINGS. These settings are shared across
save profiles; restore the player's prior selection after testing.

## Measuring instrument-group balance

An opt-in diagnostic meter now measures the stereo sum of each routed group:
melody, bass, percussion, and unclassified. It observes the real voice mixer
**after ADSR and voice volume/panning, before shared reverb, main volume and
bus saturation**. Voices in each group are summed before computing RMS, so
phase cancellation is included. Peaks and RMS use signed-16-bit PCM units,
but group sums may exceed that range before the game's final saturation.
These measurements do not include CD/movie input or the shared reverb return.

The meter does not change audio, guest memory, sample cursors or saved settings.
It stops automatically after the requested number of 44,100 Hz frames (maximum
30 seconds), is inactive by default, and resets on savestate load. Normal
playback skips the per-voice accumulation and per-frame meter calls. Untagged
legacy packs, unmatched voices and noise are explicitly unclassified; they are
not guessed to be melody. Classified roles still depend on provisional pack
routing, including the first-tone rule for shared samples.

```json
{"cmd":"shinka_nav","op":"music-meter","frames":264600}
{"cmd":"shinka_nav","op":"music-meter"}
```

The first request starts a six-second measurement; the second reads progress.
The response contains `active`, completed `frames`, and four-element `rms` and
`peak` arrays in the role order above. `frames:0` clears/disables the meter.
The completed result remains readable until another measurement or state load.

For a running debug session with **copied** checkpoints, the comparison tool
reloads each scene for each palette, settles the crossfade, writes JSON and a
Markdown table, then restores the prior Soundtrack setting even on failure:

```powershell
python tools/measure_music_balance.py --port 4384 --output output/mix-check --scene central-park:1 --scene battle:4 --seconds 6
```

Use slots appropriate to that diagnostic profile. These sequential short
replays are not sample-aligned stems, and RMS does not establish perceived
brightness or musical taste. Zero bass-group energy means that no samples
tagged as bass contributed in the window; it does not establish that the
arrangement has no low-frequency material.

The first live pass used `SHKMUS03` pack hash
`17f7c7279c2c4b7231bee24ad4f4257bc4d23f77872b13a7871f3aecd17a12c6`.
The table shows **percussion RMS relative to melodic-group RMS**, in dB:

| Copied scene | Original | DS | Sampled | Chip |
| --- | ---: | ---: | ---: | ---: |
| Central Park, six seconds | -8.6 | -12.2 | -11.6 | -8.0 |
| Idle random battle, six seconds | +4.5 | -1.5 | -0.9 | +5.0 |
| South Station, six seconds | -16.2 | -14.5 | -12.1 | -13.3 |
| Starter selection, eight seconds | +0.2 | -9.6 | -8.0 | -8.2 |

Battle bass relative to melody was +6.6 dB Original, +2.3 DS, +1.5 Sampled,
and +3.7 Chip. The current DS/Sampled battle reductions are visible in these
measurements, while Chip percussion is close to Original. South Station shows
a different result, so a universal additional percussion cut is not justified
by this pass. Instrument routing, timbre, and longer listening comparisons
remain the next checks. No mix gains were changed. North Badland W was not
verified in this pass: an older checkpoint label pointed to starter selection,
which was identified visually and recorded under its actual scene.

Local results are under `output/music-meter-01/results/` and `starter-menu/`.
All 16 native suites, 169 Python tests and Ruff passed. New tests cover role
grouping, stereo RMS, cancellation, silent frames, bounds, legacy/noise
classification, state reset, unchanged sample output and settings restoration
after a successful or interrupted measurement.

## Badlands instrument routing correction

The routing audit found that assigning instruments from program numbers alone
misclassified two `BGM018` parts. Program numbers are bank-local identifiers;
program 1 does not necessarily mean bass.

| Original route | Score evidence | Previous replacement | Current replacement |
| --- | --- | --- | --- |
| Program 1, sample 3 | 74 notes, MIDI 64–77; two tones an octave apart share the sample | Finger bass / triangle wave, bass gain | Synth strings / pulse wave, melodic gain and presence |
| Program 8, sample 11 | 48 notes, MIDI 40–50; strong low source fundamental | Piano / waveform table, melodic gain | Finger bass / triangle wave, bass gain |

DS blends the revised sampled and generated voices as before. The corrected
classification applies the existing -2 dB bass treatment to the low part and
removes it from the high part. No global EQ or mix-gain constants changed.
The strings/pulse choice is provisional; a correct musical role does not prove
that a particular replacement timbre suits the scene.

`assets/music/live-routing.json` records each override's rationale, expected
owner programs and exact MP/MV source hashes. The builder verifies those hashes
against the owned inputs and refuses changed sources, missing samples, different
owners, unsupported instruments or missing rationale. The resulting pack report
records the profile hash and each overridden route's rationale. Rebuild with the
normal command above; no external assets or additional SoundFonts are needed.

The local `output/music-live-07/` pack contains the same 42 banks and 669 routes.
Its binary differs from `music-live-06` in **only BGM018 samples 3 and 11**;
all other route records, including their PCM, remain byte-for-byte identical.
The installed pack SHA-256 is
`ac54d27caa43791f17dbd16caaf64a923ac3b3f177edb06ac09f273b976d52a1`.

With the player's navigation help, the live check reached North Badland W,
mode `0x24a`, from Pelche Oasis. An entire 56,000-byte BGM018 source bank matched
SPU RAM at `0x49c10`, confirming the actual loaded music independently of the
scene label. A new isolated checkpoint captured the stationary scene. Six-second
before/after recordings cover all four palettes at that checkpoint under
`output/music-routing-01/audio-before/` and `audio-after-final/`. Original sound
still bypasses replacement; the rebuilt pack preserves every original bank byte.
The live check establishes playback and switching; final timbre approval still
requires listening. All 16 native suites, 172 Python tests and Ruff passed.

The audit also identified percussion candidates for a later pass. BGM018 samples
9/10 are short/long high-frequency hits at score keys 80/81; the generic drum
fallback currently chooses the same snare sample for both. BATL00 sample 10 is a
non-looping, mostly high-frequency sample in the drum program with a *range* of
keys, so the single-key heuristic currently labels it clarinet. These remain
unchanged pending isolated listening and a percussion-specific profile. Their
current role tags must not be treated as verified instrument identities when
interpreting meter results.

### Listening brief: preserve the changing orchestration

The player's Original-track listening notes describe a frequent metallic triangle,
occasional timpani, an accordion-like repeated double-note figure, an occasional
bell/music-box passage, a harp-like passage, and a flute-like lead. These are
listening descriptions, not confirmed General MIDI instrument labels. Improving
this track requires distinguishing its parts rather than assigning every high
part a generic melodic voice and every low part bass guitar. In particular,
the new strings and finger-bass choices remain provisional: the low-register
part may be the struck/timpani-like sound the player describes.

The exported score provides an audition plan. Times below are seconds from the
start of `BGM018/sequence-000.mid` (about 48.18 seconds), not the running game's
playback clock. Sample IDs refer to the owned bank. Instrument hypotheses should
be confirmed by soloing original voices with their native envelopes before
authoring further replacements.

| Program / source samples | Independently observed score behavior | Listening question |
| --- | --- | --- |
| 7 / 9, 10 | 120 hits every 0.4 seconds; keys 80, 80, 81 repeat from 0.175 s. Two distinct short/long, high-frequency source samples. | Strong candidate for the metallic triangle pattern. Preserve both hit lengths; the current common snare/noise fallback loses that distinction. |
| 8 / 11 | Low notes 40–50, mostly every 1.2 seconds, beginning at 0.175 s. | Is this the timpani-like accompaniment? Register alone cannot justify finger bass. |
| 5 / 7 | A low note followed by two repeated two-note chords, at 0.4-second spacing from 0.175 s; continues across the track. | Strong rhythmic candidate for the accordion-like figure; timbre still needs isolated confirmation. |
| 2 / 4 | Repeating three-note figures, 0.2/0.2/0.8-second onset gaps; begins at 0.575 s and ends around 28.775 s. | Identify this ornament separately from the chordal accompaniment. |
| 6, 9 / 8 | Same 105-note part, with program 9 delayed by 0.4 seconds and slightly detuned. | Identify the lead/ornament and preserve its composed echo. |
| 3, 4 / 6 | Same 45-note part, beginning at 9.375/9.575 s; 0.2-second delay and slight detuning. | Candidate for one of the contrasting flute-like or bell-like passages; do not merge the two voices. |
| 1 / 3 | Sparse early notes, then a busy passage from 28.575 s; two tones an octave apart share the sample. | Identify the late lead/harp-like passage before settling on synth strings. |
| 0 / 1, 2 | Mostly three-note chords every 1.2 seconds from 0.175 s; two source key zones. | Identify the harmonic bed and retain both source zones. |

The observation supersedes any implication that the two routing corrections
finish the arrangement. No new timbre or gain changes were made while recording
this brief, and the player's active listening session was left untouched.

## Original instrument stems

`tools/capture_music_stems.py` records all original ADPCM source voices
simultaneously from a running copied-profile scene. The capture observes original
post-envelope samples and native voice panning/volume before the shared reverb,
main volume, CD input and mix saturation. It does not mute voices, rewrite score
events, alter the reverb buffer or change normal audio output. Capturing while
Original is selected also avoids alternate timbres influencing any pitch
modulation. The tool temporarily selects Original and restores the prior palette.

The native recorder allocates storage before capture, never allocates or writes
files in the audio path, and stops at an exact requested frame count. It is
inactive by default, rejects a second capture until cleared, clears on state
load, and caps storage at 256 MiB and duration at 120 seconds. The effective
duration limit depends on sample count. Debug export requires a completed capture
and an existing empty directory; it never overwrites a previous export.

Sources are stored as unclipped signed 32-bit stereo sums. The Python exporter
joins key zones and programs sharing sample assets into instrument families,
keeping composed delay/detuning voices together. Full 16-bit WAV stems share a
single headroom gain, preserving their relative balance and sample alignment.
Separate eight-second auditions select active passages and normalize each for
identification; **do not compare mix levels using those short auditions**.
Shared source assets prevent distinguishing every individual sequencer program
in these files. The manifest preserves program/sample membership for review.

```powershell
python tools/capture_music_stems.py --port 4384 --slot 1 --pack output/music-live-07/music-live.bin --export output/music-catalog-export/BGM018 --output output/badlands-stems --seconds 55
```

Use a checkpoint in the requested scene in a copied profile. The tool verifies
the pack's routing-report hash, owned export identity and complete source bank
in live SPU RAM before recording. It writes `stems.json`, a file index, raw
sources, aligned full stems, and short auditions. The tool accepts other bank
exports; each scene still needs its own live capture and listening review.
Source banks and exported music remain local owned-disc artifacts, not public
repository/release files.

The first Badlands capture produced ten source stems grouped into eight sound
families, each exactly 2,425,500 frames (55 seconds), with zero unmatched nonzero
voice samples. All eight full WAVs and eight audition clips were non-silent and
unclipped. They are under `output/music-stems-01/BGM018/`. Part membership is:
1: program 0; 2: program 1; 3: program 2; 4: programs 3/4; 5: program 5;
6: programs 6/9; 7: program 7; 8: program 8. Instrument names await the player's
ear-based identification. This validates Badlands capture, not every song.

All 16 native suites, 175 Python tests and Ruff passed. Tests cover capture
duration/reset, source isolation, headroom beyond 16-bit range, silent-frame
alignment, overwrite refusal, family grouping, shared export gain and active
audition selection. The diagnostic game was closed and settings restored before
presenting the solo previews so its full mix would not play over them.

### Batch the owned catalog without navigating the game

`tools/split_music_ost.py` splits every eligible sequence in an owned export
catalog in one invocation. It uses original decoded samples and scores; no
replacement SoundFont, running game or per-area checkpoint is required.

```powershell
python tools/split_music_ost.py --exports output/music-catalog-export --output output/ost-stems
```

Open `output/ost-stems/index.html` for a local listening page, with track/scene
labels where the source MIDI hash has a unique catalog match. Each track has
aligned full WAV stems, independently normalized eight-second auditions, and
per-family MIDI files. Key zones and shared-sample echo programs are grouped.
Program/sample IDs and input hashes remain in `stems.json`; audible names still
need listening. This is a batch conversion, not automatic instrument recognition.

**Offline WAVs are approximate auditions, not native SPU captures.** They use
linear sample interpolation, approximate register-derived envelopes and volume/
pan, and one linear score pass. Standard volume, pan, sustain and pitch bend are
handled. Custom controllers/loops, vibrato, portamento, noise mode, shared reverb
and hardware voice allocation are not emulated. Unsupported events and notes
without a declared key zone are counted per part rather than assigned invented
instruments. A silent family is a failure, not a successful empty export. Use
the native recorder when these differences matter to identification or balance.

The splitter enumerates declared sequences, including BGM031 sequence 002, rather
than assuming sequence 000 or counting every tiny cue as a song. Cues shorter
than one second, empty sequences and sequences referencing absent programs are
listed as skipped in `batch.json`. Other failures are reported and cause a
nonzero exit after the remaining tracks are attempted. A new output directory
is required; input exports and existing results are never overwritten. `--bank
BGM018` optionally limits an audition run. Audio is rendered one family at a time
and temporary family buffers are removed after WAV export.

The initial full catalog run produced 49 sequences across 42 banks, with 410
families (820 full/short WAVs and 410 MIDI splits), no failed sequences, and 623
explicitly skipped cues. Independent checks verified source hashes, WAV format,
non-silence, headroom, shared gain, full-stem alignment and split-MIDI duration.
EVO_00 reports one unrendered program-9/key-48 note outside its declared zones.
This validates export structure, not audible equivalence to native playback.
All 182 Python tests and Ruff passed; no runtime binary changed. Local results
are under `output/music-ost-split-03/` (about 4.6 GB of uncompressed audio).

### Walk between areas and capture exact original parts

With a copied-profile debug session running and the area's music loaded, the
native recorder can select the export automatically:

```powershell
python tools/capture_music_stems.py --port 4384 --pack output/music-live-07/music-live.bin --exports output/music-catalog-export --output output/area-stems-01
```

Stay in the area until recording finishes. Repeat with a new output directory
after walking to another area. All instruments are recorded together. Detection
requires exactly one complete original bank match in live SPU RAM and matching
export hashes; if music is absent or bank identity is ambiguous, the tool refuses
to guess. Specify `--export` for a known bank when necessary. Bank detection does
not identify which sequence within that bank is playing, and cached banks can
still be present; listen to confirm the scene and inspect non-silence/unmatched
counts. Default duration uses the longest substantial local sequence plus two
seconds, subject to the recorder's existing memory/duration limits. For a bank
that exceeds those limits, choose a shorter explicit `--seconds` window.

### Badlands ear identifications

The player's labels below refer to the **native** BGM018 auditions, not the new
offline approximations. No additional replacement mappings were changed during
this labeling pass.

| Part | Programs | Samples | Player identification |
| --- | --- | --- | --- |
| 1 | 0 | 1, 2 | Piano |
| 2 | 1 | 3 | String-like synth; possibly violin, uncertain |
| 3 | 2 | 4 | Bell |
| 4 | 3, 4 | 6 | Flute |
| 5 | 5 | 7 | Accordion |

Parts 6–8 await listening. IDs are specific to the BGM018 source hashes already
recorded in the guarded routing profile; they are not global MIDI program names.

## Instrument labeling notebook

The local listening library now has an editable companion workspace:

```powershell
python tools/label_music_stems.py --library output/music-ost-split-03 --native BGM018-000=output/music-stems-01/BGM018 --port 4387
```

Open the printed local address. Choose a track by title or area, play a short
isolate or its full stem, and enter an instrument name, confidence and optional
notes. **Save label** writes the record to disk; **Save & next unlabeled** (or
Ctrl+Enter) advances through remaining parts. Track progress and an unfinished
filter help with the catalog. Starting a second player pauses the first.

The Badlands native capture imports the player's five prior identifications,
including the tentative string-synth/violin description, and defaults to native
audio. Other tracks use clearly labeled offline approximations. Add repeatable
`--native TRACK=DIRECTORY` arguments as new in-game captures become available.
Matches require the bank's source hashes plus the family's program/sample sets;
the explicit track association supplies sequence context. No general MIDI
instrument names are inferred from bank program numbers.

Labels are stored separately in `output/music-instrument-labels.json` (override
with `--labels`), so regenerating audio does not erase them. Stable identities
include the source hashes, bank, sequence, programs and samples, not display part
numbers. Existing labels take precedence over imported seeds. Writes are atomic;
stale edits from another tab are rejected and disk failures remain visible with
form edits intact. The server's in-memory state changes only after a successful
write. Use one labeling server per label file. Export labels downloads the same
JSON for backup or later route authoring; labels do not automatically change
the game's replacement instruments.

The server binds only to loopback, serves explicitly indexed audio with range
support for seeking, and accepts writes only with its session token and local
origin. The UI offers a read-only `read_instrument_labels` WebMCP tool when the
browser supports it. No original music is uploaded or committed.

Validation: 188 Python tests and Ruff pass, including identity-safe imports,
persistence across store restarts, stale-write rejection, failed-write recovery,
audio path boundaries, HTTP saves/readback and byte ranges. Browser checks cover
search, full/short selection, native playback, saving an existing identification,
advancing to Part 6, reload persistence and read-only label retrieval.
