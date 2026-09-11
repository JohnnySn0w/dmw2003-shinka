# Save timing investigation

The September 9, 2026 windowed test found sustained card writes during the slow
Guardromon save animation. Removing the loading bar alone would not remove the
underlying wait. No card timing or game behavior was patched in this test.

## Setup and preservation

The user's cards and existing states were backed up under
`output/user-handoff-backup/`. Tests used a separate `output/performance-saves/`
copy with the retail BIOS backend, normal speed, and function tracing disabled.
Original card 1 SHA-256:
`bdf44e30f7e5a041c3d28ad328c5c231e964fa01461dda89c648df0f8f64b7f5`.
Cards, screenshots and raw traces remain local and ignored.

## Measured overwrite

`output/timing-save-write-full/` contains a 45-second capture of an overwrite
from the save-slot selection checkpoint. Sampling began after confirmation.

| Observation | Result |
| --- | --- |
| Successful write transactions observed | 80 |
| Written sector range | `0x0044`–`0x0093` (10 KiB total payload) |
| First / last successful write first observed | 0.5 / 29.0 seconds into capture |
| Saved message visible | Screenshot at about 30 seconds |
| Guest frame rate over capture | 50.00 frames/second |
| Sampling call time, median / maximum | 47 / 79 milliseconds |

An earlier capture's card hash stopped changing after roughly 1.5 seconds even
though writes continued. Rewriting identical sectors does not change a file
hash, so hash stability is **not** a save-completion signal. The bar progressed
while the later trace showed successful writes.

This supports investigating the guest card driver's per-sector scheduling and
the runtime's serial/card timing. It does not establish which causes the delay;
a matched original/emulator comparison and finer tracing remain necessary.
Save errors and completion acknowledgements must still work after optimization.
The user reported successful in-game saving/loading and savestates, with slow
card loading/saving. The subsequent load investigation is recorded below.

## September 11: batched memory-card loading

The resident load wrapper `0x80014d04` submits a separate asynchronous file
operation for every 128 bytes. The card library at `0x8003cba4` accepts larger
sector-aligned requests but performs its file setup and open/read/close sequence
for each request. The similarly structured wrapper at `0x80014fc4` is the **write**
path and remains unchanged.

Tests used the installed retail-BIOS runtime, normal 50 Hz playback, and copies
of cards and states under `output/card-loading/`. Measurements start after the
confirmation input has returned, so they exclude that brief input interval.

| Save body load | Original | Batched |
| --- | --- | --- |
| Last sector first observed | 25.02 s | 6.11 s |
| Successful data-sector reads | 78 | 78 |
| Sector range | `0x46`–`0x93` | `0x46`–`0x93` |
| Typical gap between sector completions | 320 ms | 40 ms within a batch; 320 ms between batches |
| Result | LOADED | LOADED |

The directory scan already completed sectors about every 40 ms. This contrast,
and the improvement without changing SIO timing, identify repeated file-operation
setup as a significant cost. The exact first-32-read cycle summary confirms the
40/320 ms pattern; wall-clock first-observed times are approximate samples.

The load requests `0x26c4` logical bytes, which the original wrapper rounds up to
78 sectors (`0x2700` bytes). The first request and retry restart stay at 128 bytes.
Later requests contain up to 1024 bytes, with a short final batch. Completion
accounting reads the library's actual serialized request length at `0x800828ec`.
This also supports a savestate captured with the old 128-byte request in flight.
Progress, destination offsets, card checksums, asynchronous completion, retries,
and error reporting continue through the original game/library routines.

The generated source changes only read-side sites `0x80014ee8` and `0x80014f04`;
generation fails if either expected site changes. No disc bytes or pinned
framework files are edited. `SHINKA_CARD_READ_BATCH=0` restores single-sector
submissions for comparison; actual pending request sizes are still accounted
correctly when restoring a batched state in that mode.

Validation so far:

- The complete `0x2700`-byte loaded body and 256-byte header buffer match the
  original run byte for byte. The same story, area, position and party were loaded.
  The installed build was also checked through dismissal of LOADED into Asuka Inn.
- A checkpoint created with batching disabled and a 128-byte request in flight
  resumed with batching enabled and produced the same complete body.
- A separate card copy with its body integrity byte deliberately set to zero
  was rejected with `MEMORY CARD error. Please check MEMORY CARD.` Game progress
  was not loaded. A different single-bit payload change was accepted by the
  existing check; this test does not establish detection of arbitrary corruption.
- Exhaustive native range tests cover every logical length from 1 through
  131072 bytes, including short tails, sector rounding, and invalid progress.
- Generator regression tests require the exact read sites and verify that the
  corresponding write-side instructions remain unchanged.

This is a loading optimization. The roughly 30-second save/write observation
above remains a separate item. Real card removal, fragmented cards, multiple save
files and additional campaign saves still merit further integration coverage.

## Reproduction tooling

With a diagnostic runtime using copied cards and its localhost debug server,
start the recorder immediately after confirming the overwrite:

```powershell
python tools/record_card_timing.py --output output/new-save-capture --card output/performance-saves/card1.mcd --seconds 45
```

The destination must be new and inside `output/`. The recorder samples every
0.5 seconds and requests a screenshot about once per second. It sends no game
input. It retains the latest 64 slot-0 transactions and removes byte payloads
from its JSONL log. This is bounded diagnostic sampling, not an exact profiler:
long stalls or very high transaction rates can lose history, and first-observed
times are approximate. Screenshots and card reads also add measurement overhead.

`runtime_probe.py` now accepts the debug server's multiline transaction JSON,
scanning delimiters once rather than repeatedly parsing a growing response.
Regression tests cover multiline responses, strings with escaped delimiters,
single-line replies and truncated responses.
