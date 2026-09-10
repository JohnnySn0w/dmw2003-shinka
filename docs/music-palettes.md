# Sampled and chiptune soundtrack auditions

Two offline BGM001 previews now use the same original note timeline:

- **Sampled:** piano, finger bass, clarinet, synth strings, and electronic drums
  from individually verified CC0 FreePats banks, rendered with TinySoundFont.
- **Chip:** generated pulse/square waves, triangle bass, a short quantized
  waveform table, synthesized pitched percussion, and noise percussion. It uses
  at most 24 simultaneous voices, with deterministic voice stealing.

These are creative arrangement prototypes, not menu options yet. The voice
assignments are provisional; they do not establish the original instruments'
identities. Song titles and scene associations remain unmapped. Audition before
expanding the profile to other banks.

## PS1 hardware versus a chiptune palette

The [PS1 SPU](https://psx-spx.consoledev.net/soundprocessingunitspu/) plays sampled
ADPCM voices with pitch control, envelopes, noise, and reverb. Our pinned runtime
already contains an SPU implementation (`runtime/src/spu.c`). Another faithful
SPU implementation would aim to reproduce the original samples and effects.

The new chip renderer changes the sound sources to generated waveforms. Its
24-voice budget borrows the PS1's scale, but its oscillators, linear envelopes,
noise, interpolation, and mixing are **not hardware emulation**. Pulse edges are
smoothed with polyBLEP; the 32-step lead table retains intentional quantization.
It does not emulate an NES, Game Boy, or FM chip either. An authentic specific-chip
mode would require a further backend and arrangement constraints.

## Reproduce the auditions

Use Python 3.12 and 7-Zip for the tested Windows path. Dependencies are optional
for the game/runtime but required for these preview tools:

```powershell
python -m pip install -r tools/requirements-music.txt
python tools/music_fetch_banks.py --output output/music-banks --seven-zip 'C:/Program Files/7-Zip/7z.exe'
python tools/music_preview.py output/music-bgm001/sequence-000.mid --backend soundfont --output output/audition-sampled
python tools/music_preview.py output/music-bgm001/sequence-000.mid --backend chip --output output/audition-chip
```

First export BGM001 using [the music exporter](music.md). The default arrangement
accepts that exact exported main sequence, checked by SHA-256. Each render creates
`preview.wav` and `preview.json` in a new directory. It never starts an audio device.
Use a fresh destination for reruns; existing directories are refused.

For a local dependency install without changing the Python environment:

```powershell
python -m pip install --target output/music-synth-deps -r tools/requirements-music.txt
$env:PYTHONPATH = Join-Path (Get-Location) 'output/music-synth-deps'
```

`assets/music/bgm001-audition.json` controls program-to-instrument assignments,
pan, gains, percussion key remaps, and chip ADSR. All channel/program/key numbers
are zero-based. Original channel 9 is routed as a melodic part, not automatically
converted into a General MIDI drum channel. Every selected SF2 has its instrument
at bank 0, preset 0, including the electronic drum bank.

The drum SF2 also uses its own key layout (kick at 48, snare at 50, and so on).
`soundfont_key_map` translates the arrangement's percussion keys into that layout.
The bass SF2 covers keys 26–45. Its route selects samples one octave down and
applies +12 semitones of synth tuning, preserving the score pitch while keeping
all bass notes within the bank's playable range. These adjustments affect only
the SoundFont backend; they do not transpose the chip arrangement.

The audition renderer currently requires one instrument per source channel.
Unknown programs, missing percussion mappings, changed MIDI, and changed bank
files are rejected. For another song, create and inspect its own profile rather
than copying BGM001 assignments and merely changing the hash.

## Assets and attribution

`assets/music/cc0-banks.json` pins source URLs, credits, archive members, and SHA-256
hashes for both downloads and extracted SF2 files. The downloader verifies those
hashes and reads only the selected archive member into memory; it does not extract
paths from an archive onto disk. Reusing an existing bank also verifies its hash.

The selected assets' project pages and included readmes explicitly identify CC0:

| Bank | Source and credits |
| --- | --- |
| Upright Piano KW, small 20190703 | [FreePats piano](https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html), recorded by Gonzalo and Roberto |
| Finger Bass YR 20190930 | [FreePats bass](https://freepats.zenvoid.org/ElectricGuitar/clean-electric-bass.html), Andrea Biasior; FreePats edits by Roberto |
| Synth Strings 1 20200528 | [FreePats strings](https://freepats.zenvoid.org/Synthesizer/synth-strings.html), synthesized for FreePats with ZynAddSubFX/Yoshimi |
| Synthesizer Percussion 20220718 | [FreePats percussion](https://freepats.zenvoid.org/Percussion/electric-percussion.html), Roberto |
| Clarinet 20190818 | [FreePats clarinet](https://freepats.zenvoid.org/Reed/clarinet.html), Tyler and Kaili Dence; bank/loops by Roberto |

This is a curated five-bank palette, not a full General MIDI set. FreePats' full
GM compilation has different licensing. CC0 for these instrument banks does not
change ownership of the game's sequences or of audio rendered from them. Bank
downloads, extracted game assets, and rendered previews stay in ignored local
storage. The repository contains the catalog, mappings, and tooling only.

The optional renderer is [TinySoundFont's Python binding](https://github.com/amberwhitehead/tinysoundfont-pybind),
version 0.3.7, under MIT. Its installation carries its dependency notices. The chip
oscillator implementation is local source and needs no downloaded instrument data.

## Validation and current limits

On 2026-09-10 both full BGM001 renders completed at 44,100 Hz stereo, with
2,741,830 frames: approximately 60.173 seconds of score plus a two-second tail.
Both target RMS 0.1, with gain capped at a peak of 0.89 and a 25 ms tail fade;
there is no clipping limiter. The first sampled/chip peaks were approximately
0.565/0.724 after correcting SoundFont key coverage. Matching RMS is an audition
aid, not perceptual loudness matching.
The chip run reached 24 voices and stole six voices, preferring releasing voices
before the oldest held voice.

The sampled renderer preflights all 138 used channel/key combinations in isolation
and rejects any silent key. This caught missing drum mappings and out-of-range
bass notes that a non-silent full-song render would have hidden. All 138 pass with
the corrected profile. This probe uses velocity 100 and a 250 ms audition window;
it is not a full validation of every velocity layer or long-attack instrument.

Nine synthetic tests cover tempo/sample timing, melodic channel 10 routing,
mapping/hash failures, block-size-independent synthesis, sustain/release,
voice stealing, pitch bend/pan/volume, silent-key rejection, and output tail/headroom. Run the Python
suite after installing NumPy:

```powershell
python -m unittest discover -s tests
```

Both backends handle note events, volume, pan, expression, sustain, channel
reset, all-notes/all-sound-off, and pitch bend with a two-semitone range. Custom
PS1 controller commands are counted in `preview.json` and ignored; their loop/effect
semantics remain unresolved. Other unsupported
events are likewise reported. Sequence loops are not expanded. SoundFont samples
use their own authored tuning/envelopes, and chip voices use the audition ADSR;
neither reproduces the original VAB tone behavior. Effects are currently dry.

The previews establish working render paths, timing, and output bounds. They
still need listening feedback on instrument choices and balance. Runtime music
selection, track identification, transitions, loop timing, and separation from
sound effects remain follow-up work before adding soundtrack settings.
