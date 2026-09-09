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
Load timing has not been measured independently. The user reported successful
in-game saving/loading and savestates, with slow card loading/saving.

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
