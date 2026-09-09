# Initial investigation

Historical first-pass notes. The [groundwork audit](groundwork-audit.md) supersedes the open questions below about image hashing, hidden directories, and local music extraction.

## Observed in the local image

- Single-track BIN/CUE image, MODE2/2352.
- BIN size: 692,146,560 bytes.
- ISO volume identifier: `DMW3`.
- Root directory entries:

| Entry | LBA | Size in bytes |
| --- | ---: | ---: |
| SYSTEM.CNF;1 | 23 | 70 |
| SLES_039.36;1 | 24 | 923648 |
| DUMMY.;1 | 276901 | 35283682 |

The visible directory does not expose the bulk of the game's assets. Locating the internal asset index or using a compatible extractor remains necessary. The image has not been modified or hash-validated against a reference dump.

## Experience

Normal EXP and Digivolution EXP should be investigated separately. A reward-tool author reports separate scaling and a 10-point per-battle DV EXP cap. This is a lead, not verification of the local executable or approval to run that tool.

Source: [reward editor author's post](https://www.reddit.com/r/digimon/comments/1vqasrz/battle_rewards_multiplier_for_digimon_world_3/).

Before implementing a patch:

1. Identify the relevant reward data or code in this exact release.
2. Validate original bytes and supported image identity.
3. Implement configurable multipliers, accounting for rounding, overflow, and the DV EXP cap.
4. Preserve the input image and rebuild sector integrity information as required.
5. Compare known battle rewards in the emulator before and after patching.

## Music

Game-specific extraction work identifies SEQ/SEP sequences and VH/VB instrument-bank components. These are MIDI-like sequences with sampled instruments, not simply interchangeable standard MIDI files. This has not yet been independently confirmed by extracting the local image.

Potential approaches:

- Replace instrument samples while retaining sequences, subject to bank layout, tuning, looping, and PS1 sound-memory limits.
- Render arrangements with modern instruments, then investigate a separate mechanism for synchronized in-game recording playback. Such a mechanism is not implemented or verified here.

Sources:

- [Game-specific extraction findings](https://hcs64.com/mboard/forumlong.php?showthread=44576)
- [PlayStation audio file formats](https://psx-spx.consoledev.net/cdromfileformats/)
- [PlayStation SPU and its 512 KB sound RAM](https://psx-spx.consoledev.net/soundprocessingunitspu/)

Next milestone: extract one track from the local image, identify its sequence and instrument bank, and produce a listening comparison before attempting reinsertion.
