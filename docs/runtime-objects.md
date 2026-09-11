# Runtime controller object map

`tools/inspect_runtime_objects.py` inspects the controller hierarchy from one
2 MiB main-RAM read, or analyzes an existing raw snapshot offline. It does not
load a save, inject input, change settings, or arm tracing. Use a diagnostic
instance with a copied save profile for live captures.

```powershell
python tools/inspect_runtime_objects.py --port 4383 --expect-mode 0x600 --output output/battle-motion/objects.json --save-ram output/battle-motion/ram.bin
python tools/inspect_runtime_objects.py --ram output/battle-motion/ram.bin --output output/battle-motion/offline-objects.json
```

Output paths must be new and distinct. A mode mismatch fails without saving the
capture. Keep snapshots under ignored `output/`: they contain original game data
and player state. The JSON includes a snapshot hash, but does not identify the
runner executable or overlay version; record those separately when comparing
builds. A live read adds diagnostic work, so do not use it during CPU benchmarks.

## Recognition and limits

The supported controller header has eight state-setter callbacks at offsets
`+0x28` through `+0x44`. The inspector matches that complete signature and checks
alignment, RAM bounds, and the update callback. It reports controller addresses,
update callbacks (`+0x48`), four raw state words (`+0x0c` through `+0x18`), child
tables (`+0x24` / `+0x20`), parent links, and reachability from the current mode
owner at `0x8005ccbc`. Nonempty child slot indices are preserved.

Physical RAM, KSEG0 and KSEG1 addresses are normalized for graph links. MMIO,
unaligned pointers, out-of-bounds tables, and counts over 256 are not followed.
Invalid tables and unrecognized children remain visible in the report.
Traversal terminates on cycles and repeated edges. JSON uses a flat graph.

**A signature is not proof of a live allocation.** Old headers can remain after
deletion; pooled or independently owned objects can be detached from the mode
owner. Even reachability is pointer evidence, not proof that a callback ran.
Modified headers may be missed. Do not patch a candidate based only on its
address or callback: establish live overlay identity, ownership and behavior.

## Initial battle validation

The copied command-menu checkpoint contained 72 signature candidates, of which
63 were reachable from the mode owner. Opening the technique menu produced
81 candidates and 72 reachable objects. The combatant group had two model
controllers with callback `0x80083e0c`; a separate environment branch used the
same callback. Matching that function alone would include scenery in an
animation-speed patch.

Targeted RAM-write traces then identified combatant clip, progress and completion
stores, including paths absent from the function-entry sample. See the
[animation investigation](battle-animation-speed.md#live-model-timeline-audit--2026-09-11).
Ten synthetic tests cover pointer aliases, truncated reads, cycles, dangling
edges, detached headers, and child-table limits without original game data.
