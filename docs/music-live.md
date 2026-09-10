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

These are provisional **sample-level palettes**, not the exact arrangements in
the earlier offline previews. Asuka's sampled/chip choices start from its profile;
other banks use recorded automatic choices that need listening review. A sample
shared by multiple original tones uses the first tone's route. The live DS mix
is a sample/chip blend, whereas the offline DS preview routes whole MIDI parts
between synths. Neither Chip nor DS claims to emulate another sound chip.

The VAB root key and fractional tuning set each replacement sample's reference
pitch; the original SPU pitch register then drives its playback rate. Original
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
reset, and malformed-pack fallback. It uses synthetic data rather than game
assets. Run `ctest --test-dir build-windows -C Release -R music_live`.

The local headless game check used a copied save profile, the in-game SETTINGS
row, an Asuka-area → Central Park transition, and a random encounter. A battle
checkpoint was then loaded in the final build, all four palettes produced live
audio, and real attack inputs completed the encounter and returned to the field. Captures
of all four palettes had nonzero audio and no clipped samples in the short
comparison windows. This establishes switching, not the musical tastefulness
of all 42 banks or end-to-end listening coverage of the campaign.

Developer diagnostics: `{"cmd":"shinka_nav","op":"music"}` returns the saved
palette, pack status and count of matched note starts. Adding `"palette":0..3`
uses the same persistent setter as SETTINGS. These settings are shared across
save profiles; restore the player's prior selection after testing.
