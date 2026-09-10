# Music extraction and instrument groundwork

The owned European disc's 30 `MPBGM`/`MVBGM` pairs successfully export to
standard MIDI, decoded sample WAVs, and instrument metadata. This is offline
tooling. [Sampled, chip, and DS-inspired auditions](music-palettes.md) now render
the first main sequence. The DS-inspired hybrid is the preferred direction;
in-game replacement playback is still pending.

## Reproduce

Use Python 3, with no additional packages required. From the repository root,
extract a pair from your own disc into ignored storage:

```powershell
python tools/audit_disc.py 'path/to/owned-disc.bin' --output output/music-inputs --extract-file MPBGM001.BIN --extract-file MVBGM001.BIN
python tools/music_export.py output/music-inputs/MPBGM001.BIN output/music-inputs/MVBGM001.BIN --output output/music-bgm001
```

Choose a new export directory for each run. The exporter refuses an existing
destination, reads its inputs without modifying them, and records their SHA-256
hashes in `music.json`. The supported layout is a two-entry MP pack containing
VAB version 7 and SEP version 0, paired with a one-entry MV sample body. Bounds,
counts, sample references, and sequence event boundaries are checked. This is
format validation, not verification against a pinned disc hash.

Each export contains:

- `sequence-NNN.mid`: one-track, format-0 MIDI with explicit event statuses,
  tempo changes, time signature, and the original controller values.
- `sample-NNN.wav`: mono 16-bit PCM at a 44,100 Hz reference rate, with sample
  loop points in a WAV `smpl` chunk when present.
- `music.json`: sequence timing and program usage, programs without a matching
  local instrument, controller timelines, bank/program volume and pan, tone
  key ranges and sample references, raw tuning/ADSR/modulation fields, and
  sample extents and loop points.

Keep these generated game assets local. `output/` and `extracted/` are ignored
by Git; no music or samples are distributed with this source.

## What the local data establishes

`MPBGM001.BIN` contains a `pBAV` instrument header and a `pQES` sequence set.
Its paired MV pack contains 82,672 bytes of SPU ADPCM sample data. The bank has
12 programs, 17 tones, and 16 samples. A program can contain several tones with
different key ranges, and programs can share samples with different envelopes.

Its main sequence lasts approximately **60.173 seconds for one linear pass**,
at 480 ticks per quarter note, with 4,717 source events. Sony's sequence tempo
event omits the payload-length byte required by standard MIDI. The exporter
inserts that byte and normalizes running status; copying the raw event stream
into a MIDI file would produce an invalid tempo event.

The other 15 entries in this pack are very short program-127 cues with no
matching instrument in the local bank. Their game-specific purpose is unresolved.
Across all 30 BGM pairs there are **480 sequence entries and 475 sample files**;
those entries are not a count of distinct songs, and samples may repeat between
banks. All 30 substantial BGM sequences now match community soundtrack labels;
see the [per-track listening guide](music-listening-guide.md). BGM031's music is
sequence 002, not its tiny sequence 000. Scene reuse still needs runtime checks.

Instrument numbers are bank-specific. In BGM001, zero-based channel 9 uses a
melodic program; a General MIDI player that forces percussion onto MIDI channel
10 will play it incorrectly. A richer-instrument arrangement needs an explicit
mapping of these original voices, including percussion key splits.

## Fidelity limits and validation

WAVs are reference-rate sample decodes, not complete instrument presets. Their
neutral `smpl` unity note is 60; actual tone root keys and raw fine-tuning values
are in the manifest. Exact tuning conversion remains to be verified. Tone ADSR,
pitch modulation, reverb, voice allocation, and mixing are not rendered. Sample
loops are decoded once: manifest ends are exclusive, WAV loop ends are inclusive.
`consumed_adpcm_bytes` excludes padding after the first sample end block.

Sequence controller values are preserved without interpreting custom commands.
Sequence loops are not expanded, so the reported duration is a linear timeline,
not a claim about how long the music plays in-game. Preserved controllers may
also need translation before driving a replacement synthesizer.

Seven synthetic tests cover event timing and conversion, running status,
controller/SysEx preservation, malformed input, ADPCM prediction and signs,
sample loops, sparse program mapping, unmatched programs, and safe export.
Run them with:

```powershell
python -m unittest discover -s tests -p test_music_export.py
```

On 2026-09-10, all 30 owned BGM pairs parsed successfully. Independent Mido
1.3.3 reads of all 480 exported MIDI files matched PPQN, event counts, note-on
counts (55,821 total), and calculated durations. Python's WAV reader verified
all 475 sample files' frame counts and PCM format. These checks establish file
structure and timing, not an audible match to the game's synth. A later pass
also exported 12 battle/title/event pairs (192 entries); these have not received
the same independent Mido audit. Eleven substantial sequences match community
track labels; the title-bank sequence remains unidentified. COMMON contains
multiple bank/score entries and is not supported by the single-pair exporter.

The [live instrument palettes](music-live.md) now run beneath the game's original
sequencer, preserving its controller and loop handling. Next: refine their
instrument choices and verify scene reuse. The separate offline MIDI renderer
still needs controller/loop interpretation; original-instrument export tuning
remains a separate fidelity task.

Format references: the author-maintained reverse-engineering documentation for
[VAB sample banks](https://psx-spx.consoledev.net/cdromfileformats/#cdrom-file-audio-sample-sets-vab-and-vhvb-sony),
[SEQ/SEP sequences](https://psx-spx.consoledev.net/cdromfileformats/#cdrom-file-audio-sequences-seqsep-sony),
and [SPU sample decoding](https://psx-spx.consoledev.net/soundprocessingunitspu/).
Counts and game-specific observations above come from the local disc data.
