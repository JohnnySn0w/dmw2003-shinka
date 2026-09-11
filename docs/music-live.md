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
