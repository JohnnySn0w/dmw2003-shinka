# Opening-movie queue and polling audit

This records source inspection and a bounded trace of the owned European
opening movie. It does not establish the behavior of every STR or authorize
skipping the intermediate states described below.

## Queue layout and consumer

The consumer at `0x8002BF5C` reads these controls:

| Guest address | Observed use |
| --- | --- |
| `0x80081474` | Consumer slot index |
| `0x8008147C` | Control checked while handling state 1 |
| `0x80081488` | Header-table pointer |
| `0x8008148C` | Header count, used to locate the payload area |

In the copied checkpoint, the table is at `0x800E1B8C` with 32 entries of
32 bytes. These are observed pointer/count values, not constants suitable for
unconditional patching. The low halfword of each header becomes its state.

On state 2, the consumer writes state 4, returns zero, and publishes both a
header pointer and a payload pointer to its caller. The payload calculation is
`header_base + header_count * 32 + consumer_index * 2016`. Other states normally
return one; state 1 also has a housekeeping path that resets the consumer index
and can clear the header state. Therefore the whole consumer is not a pure
read-only poll that can be replaced unconditionally.

The opening overlay's loop at `0x800835F0` calls the consumer, checks its return
at `0x800835F8`, and decrements register `s0` in the branch delay slot. It repeats
at `0x80083600` while the timeout is nonzero; readiness and timeout have separate
exits. Any future shortcut must preserve this countdown and execute the real
exit path.

## Observed state writers

A diagnostic run used `PSX_DEBUG_FMV_QUIET=0` and armed a write trace only over
the header table. The complete retrieved trace contains 8,414 writes across
guest frames 2389–2643 (about five seconds plus command handoff). Retrieval used
small frame windows to avoid the debug command's 2,048-entry response limit;
all available entries were accounted for. It was separate from performance
measurements. No guest memory was edited.

| Writer / provenance | Change | Count in this window |
| --- | --- | ---: |
| CD DMA channel 3, initiator `0x8002CAFC` | Full word `0x80010000 → 0x80010160` | 667 |
| CPU `0x8002C908` | Low halfword `0x0160 → 3` | 641 |
| CPU `0x8002C908` | `1 → 3` | 26 |
| CPU `0x8002BD10` | `3 → 2` | 76 |
| CPU `0x8002BFCC` | `2 → 4` | 76 |
| CPU `0x8002BEFC` | `4 → 0` | 76 |
| CPU `0x8002BEFC` | `3 → 0` | 589 |
| CPU `0x8002C6AC` | `0x0160 → 1` | 26 |
| CPU `0x8002C6D8` | Full word `0x80010000 → 0x80010001` | 26 |
| CPU `0x8002BF9C` | `1 → 0` | 26 |

The DMA initiator is a provenance tag, not a CPU instruction executing each
deferred write. Source inspection independently confirms the consumer's
`2 → 4` handoff and return-value behavior. State 0 is released, state 2 is ready
for this consumer, and state 4 has been claimed. State 3's wider lifecycle and
the precise meaning of the state-1 control path still need further study.

Most importantly, **incoming CD data and the readiness state share a header**.
The poll does not watch a separate CPU-only flag. Ignoring all DMA writes would
discard changes to the very memory being polled. The complete trace is retained
locally in `output/mdec-inline/wait-audit.json`.

## Why this is groundwork rather than a polling change

The generic idle detector requires stable loop registers (or one decrementing
timeout), no stores, and no MMIO between repeated observations. Its store count
includes DMA writes. Ignoring unrelated writes could help some waiters, but this
queue demonstrates why ignoring DMA globally is insufficient: headers are also
DMA destinations, and observation must respect intermediate memory visibility.

The current runtime reports idle skipping disabled, with zero skips. Earlier
generic and movie-specific poll-boundary experiments already showed no useful
gain; this audit does not re-enable them or claim the current detector is
actively rejecting this loop. A future experiment needs read/write overlap
tracking or a validated queue-specific contract, preservation of timeout and
interrupt timing, and matched replay evidence. See the
[runtime timing map](runtime-timing-map.md) for the device-service contract.
