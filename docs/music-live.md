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
other banks use recorded automatic choices that need listening review. A sample
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
