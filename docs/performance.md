# Runtime profiling

## Reading this report

This is a dated evidence log. Earlier targets and limitations describe the build
tested in that section, not necessarily the current implementation.

- **Battle geometry:** the retained six-routine native unit reduced process CPU
  per frame by 31.4% in the matched idle-battle test below. This is optional and
  does not establish a campaign-wide speedup.
- **Memory cards:** see the separate [read/write timing report](save-timing.md).
- **Movies:** native decoder/transfer work and fewer redundant scheduling checks
  improved short samples to about 50 guest updates/sec; longer stutter remains.
- **Memory:** default-off retrospective history avoids a 128 MiB allocation;
  repeated tests did not establish a CPU speedup from that change.
- **Background use:** [minimizing suspends offline gameplay](minimized-pause.md).

For measurement tools and subsystem relationships, see [host stack profiling](host-stack-profiling.md)
and the [runtime timing map](runtime-timing-map.md).

## Opt-in retrospective RAM history — 2026-09-11

The debug server's catch-all RAM-write ring allocated 4,194,304 entries of
32 bytes each and continuously filled them during eligible execution. Shinka
now allocates this 128 MiB buffer only when `PSX_WRITE_HISTORY` is enabled before
launch. The existing null-buffer path skips recording. Targeted address traces,
write fingerprints, counters, code invalidation, and device scheduling are
unchanged. This adjustment lives in Shinka's generated debug-server copy;
the pinned dependency is untouched. See the
[recording instructions](host-stack-profiling.md#retrospective-ram-write-history).

Four isolated launches used the same executable/map, copied movie and battle
checkpoints, seven seconds warmup, and twenty seconds measured per scene.
Order was on/off, then off/on. No compiler or stack sampler ran during these
measurements. The profiler verified each loaded image and recorded its hashes.

| Checkpoint / pair | History on CPU ms/update | History off CPU ms/update |
| --- | ---: | ---: |
| Movie, first | 17.953 | 17.500 |
| Movie, reversed | 17.594 | 17.842 |
| Battle command menu, first | 7.524 | 7.734 |
| Battle command menu, reversed | 7.531 | 7.469 |

The direction of the small CPU difference changed on repetition in both scenes,
so **no CPU speedup is established**. The retained benefit is the avoided
128 MiB allocation and continuous history writes. Process private-memory
measurements were approximately 125–133 MiB lower with recording off across
the matched pairs; resident-memory differences varied with paging and other
allocations. All eight samples held 49.998–50.049 guest updates/sec and recorded
zero new host audio underrun samples. This is a memory improvement, not a fix
for all remaining playback cost.

Validation confirmed default-off history at three movie checkpoints, the title
menu, and the battle command menu. Presented captures showed clean movie borders
and intact title/battle rendering. Explicit opt-in allocated the ring and
returned eight recent write records. With the option unset, targeted traces
still recorded writes, per-frame write fingerprints continued advancing, and
resetting catch-all history left it unallocated. A battle replay returned to
the field with all 7,904 party-record bytes matching the earlier reference.
All 97 Python tests, Ruff, and twelve native suites passed. The runtime build
had only the existing warning for the intentional debug crash-test routine;
that command was not invoked.

Local measurements and validation artifacts are retained under ignored
`output/write-history/`. Runtime candidate SHA-256:
`7e44fb087919d754fd7db7e217287f97bf48bcc0bdb7bec789b2cc6374a1a502`.

## MDEC specialization experiment and queue audit — 2026-09-11

The next compiler-only experiment forced the shared MDEC DMA service routine
to inline into its two constant-channel callers. Disassembly confirmed that
the shared variable-divide routine disappeared and the output path used
constant-divisor arithmetic. Its transfer body, readiness checks, cycle
accumulators, writes, and completion behavior were unchanged.

It did not improve playback CPU cost. Two matched movie comparisons, in
baseline/candidate then candidate/baseline order, used seven seconds warmup
and twenty seconds measured:

| Pair | Baseline CPU ms/update | Specialized CPU ms/update |
| --- | ---: | ---: |
| First | 17.422 | 17.484 |
| Reversed | 17.766 | 17.781 |

Both paths held about 50 updates/sec. The specialization was removed and the
proven build configuration restored. Local source/build/measurement evidence
is retained in `output/mdec-inline/`; no new runtime optimization is claimed.

A separate [movie queue audit](movie-queue-audit.md) recorded the consumer,
timeout loop and all 8,414 writes in a bounded header-table trace. CD DMA writes
the same memory later used for readiness flags. This rules out treating that
flag as CPU-only and reinforces the need to preserve intermediate observations
in any future wait-loop optimization. Existing idle skipping remains disabled;
earlier unsuccessful generic and movie-specific experiments were not re-enabled.

One comparison attempt encountered an executable still locked during shutdown;
the replacement failed and the existing counter-consistency check rejected its
measurement. No profile from that attempt was accepted. The profiler now checks
live/on-disk PE identity against the supplied map **before loading a save or
reading counters**, and records executable/map hashes. The live validation
rejected a stale map without performing its requested battle-state load, then
accepted the correct map and recorded schema-2 provenance. The new checks also
cover Windows rewriting the mapped ImageBase during ASLR. A timestamp alone
is not a cryptographic pairing guarantee; keep each map with its executable.

All 97 Python tests, Ruff, and twelve Shinka native suites passed. The restored
runtime built without warnings. The previously installed build remains in use.

## Caller stacks and opt-in pixel history — 2026-09-11

A new [Windows caller-stack sampler](host-stack-profiling.md) captured 1,631
opening-movie stacks. Device service appeared in 57.45% of samples, but that
included presentation callbacks and pacing waits. Excluding presentation,
device-service stacks accounted for 570 samples (34.95%). MDEC transfer service
appeared in 9.81%; the display-history recorder appeared in 7.42%, including
graphics-driver waits. These are sampled wall-time residency figures, **not
inclusive CPU percentages**. Inlining and tail calls also limit attribution.

The useful finding was an avoidable host-side cost: the debug display-history
ring reads both the displayed area and full VRAM back from the GPU at each
eligible frame. Shinka now leaves this recorder off unless `PSX_DISPLAY_RING`
is explicitly enabled before launch. This also avoids its 84 MiB allocation.
The pinned framework is unchanged; the adjustment is in Shinka's generated
debug-server copy. One-shot screenshots, presented-frame capture, GPU command
history, navigation, and the debug server remain available. Exact historical
pixel comparisons require `PSX_DISPLAY_RING=1`; they cannot recover prior frames
from a run where capture was disabled.

Separate, unsampled comparisons used the same executable and environment
toggle, copied checkpoints, seven seconds warmup, and twenty seconds measured:

| Checkpoint | History enabled CPU ms/update | History disabled CPU ms/update | Reduction |
| --- | ---: | ---: | ---: |
| Opening movie, repeated pair | 18.859 | 17.844 | 5.4% |
| Battle command menu | 8.835 | 7.781 | 11.9% |

These samples held about 50 guest updates/sec and recorded zero new host audio
underrun samples. Guest scheduler, RAM-write, and MMIO activity remained close.
The repeated movie pair was measured off-then-on, reversing the exploratory
on-then-off pair (17.813 vs 17.063 ms/update). A short compiler run overlapped
the exploratory disabled run, so only the uncontended repeated pair is used
in the table. Host clocks and scheduling varied between runs: these results
are checkpoint measurements, not a campaign-wide speedup guarantee.

A second diagnostic capture with history disabled collected 1,637 complete
stacks, with no display-history path present. Device service excluding
presentation appeared in 602 samples (36.77%). The median suspend/copy/resume
interval was 61.5 microseconds, p95 91.7 microseconds. These sampled runs are
kept separate from the CPU acceptance measurements. The tool records loaded
module identities and stack-depth diagnostics; the summarizer validates the
matching map and distinguishes leaf, inclusive, and caller-edge counts.

Final-build validation covered default-off history, explicit opt-in history,
one-shot captures, title and battle rendering, and three movie checkpoints with
clean borders. A battle replay returned to the field with all 7,904 party-record
bytes matching the earlier verified outcome. All 91 Python tests, Ruff, and
12 Shinka native suites passed. The standalone profiler also builds separately
without original game data. Evidence remains in `output/host-profiler/` and
the replay in `output/memory-lto/display-history-off-outcome.json`.

The next scheduler investigation should focus on device service after excluding
presentation/pacing and on actual transfer callers. Removing diagnostic GPU
round trips required no change to DMA timing, intermediate RAM visibility, or
interrupt order; those contracts remain prerequisites for larger batching work.

## Follow-up experiments and publication — 2026-09-11

Three further experiments were built and measured from the same copied opening
movie checkpoint. Each sample used seven seconds of warmup and twenty seconds
of ordinary-speed playback. None showed a convincing CPU improvement, so all
three implementations were removed; the installed proven optimizations remain.

| Experiment | Baseline CPU ms/update | Candidate CPU ms/update | Outcome |
| --- | ---: | ---: | --- |
| Stop querying after the minimum one-cycle deadline | 20.875 | 20.860 | No meaningful gain despite ~341,000 early exits/sec |
| Skip SPU enable checks when its next possible sample cannot win | 20.375 | 20.560 | No gain despite reducing SPU deadline queries ~97% |
| Extend LTO to memory/diagnostic helper units | 19.438 | 19.371 | Difference within sequential-run noise |

The first two preserved the global minimum in 317,649 and 235,298 synthetic
cases respectively, including zero deadlines, simultaneous events and boundary
clocks. They did not batch transfers or skip device service. Passing equivalence
tests did not establish a useful performance gain. The third changed compiler
visibility rather than runtime logic; its only warning concerned the existing
intentional `synth_recurse` crash-test command. That command was not invoked.

These are separate sequential comparisons, not a ranking of builds across the
whole table: host scheduling and clocks can vary. In particular, the audio-bound
candidate recorded 164 new underrun samples; the baseline recorded none. The
experiment therefore does not justify even a neutral-performance replacement.
Local evidence and rejected implementations remain in `output/event-minimum/`,
`output/audio-deadline/`, and `output/memory-lto/`.

This narrows the next investigation: fewer deadline checks alone are not a
reliable proxy for saved CPU time. Attribute inclusive CPU cost during actual
movie transfers before introducing a retained-deadline cache or changing transfer
granularity. Those larger changes still require explicit invalidation and
intermediate-memory-visibility contracts.

The previously verified movie/battle native units, live-byte reference guards,
reduced-spin pacing, device LTO, CD deadline fix, profiling tools and timing map
are published together. The Windows build script also builds and runs
all twelve Shinka native suites, including title-logo, CD-deadline and pacing
checks. Only generators and runtime integration are published; game-derived
native code remains generated locally from the user's disc.

Final checks passed: 86 local Python tests, Ruff, and all twelve Shinka native
suites. A fresh replay of the copied battle returned to the field with all
7,904 bytes of party records identical to the earlier verified outcome. The
three new experiments are absent from the final build.

## CD deadline correction and reusable timing audit — 2026-09-10

The controller's event prediction advertised an already-delivered CD response
as due immediately. Delivery itself correctly refused to re-raise that response,
but the global scheduler kept servicing devices at one-cycle intervals until
the guest acknowledged it. The generated CD source now checks the same delivery
latch before advertising that presentation deadline. Real pending responses,
sector arrivals, acknowledgement behavior, I_STAT and DMA visibility remain.

The [runtime timing map](runtime-timing-map.md) documents the movie data path,
the distinction between CD and interrupt-controller acknowledgements, scheduler
causality, source observation points and future investigations. This is a
runtime prediction/delivery mismatch, not an original-game delay mechanism.

`tools/profile_scheduler.py` records scheduler counters alongside Windows CPU
time, guest updates, scene state and audio underruns, using read-only process
memory access. It does not suspend the game. The baseline and corrected runs
use the **same binary**, toggled with `SHINKA_CD_DEADLINE=0` / `1` at launch.
The correction is enabled by default and is independent of save-state data.

Same copied movie checkpoint, seven-second warmup, twenty-second measurements,
ordinary speed, prior LTO/reduced-spin changes enabled:

| Measurement | Original prediction | Corrected prediction |
| --- | ---: | ---: |
| Guest updates/sec | 49.998 | 49.999 |
| Process CPU ms/update | 18.375 | 17.875 |
| Global deadline queries/sec | 4,685,280 | 4,225,576 |
| Device-advance passes/sec | 4,357,855 | 4,043,312 |
| Queries seeing a latched CD response/sec | 509,132 | 49,792 |
| Guest RAM stores/sec | 2,000,813 | 2,000,790 |
| Guest MMIO accesses/sec | 81,202 | 81,207 |
| New host audio underrun samples | 0 | 0 |

The measured reduction is **9.8% in global deadline queries** and **2.7% in
process CPU per update**. Nearly unchanged guest RAM/MMIO activity supports
removal of redundant scheduling rather than less guest work. The latched-CD
counter counts visits that see an already-delivered response, not new IRQs.
The remaining visits with the correction enabled come from other reasons to
query devices; the stale CD presentation no longer sets their deadline.
These are sequential runs with potentially varying host clocks and scheduling,
not a guarantee of a campaign-wide speedup. Evidence: `output/scheduler-01/`.

All eleven Shinka native suites and five focused profiler tests pass. The new
native test uses the actual pinned delivery, re-arm and deadline functions;
it checks delayed delivery, no repeat after I_STAT acknowledgement, new response
generations, controller masks, pending responses and sector deadlines. No broad
transfer batching or deferred device advancement has been introduced.

An 86.3-second observation from the copied movie checkpoint through its natural
title transition held 50.002 updates/sec with zero new host audio underrun
samples. Start also skipped correctly after another restore. The idle battle
check held 50.064 updates/sec at 7.740 process CPU ms/update; importantly, it saw
**zero latched-CD queries**, so its CPU difference from previous runs should not
be credited to this correction. This case primarily targets active disc/IRQ
traffic; benefits to other loading scenes remain to be measured.
The frame-counted battle replay returned to Central Park, with all 7,904 bytes
of the eight party records identical to the earlier verified outcome. A settled
field screenshot was inspected after the transition. The diagnostic process
was closed; the updated Release executable is ready for normal play.

## Device compilation and reduced-spin pacing — 2026-09-10

The Windows Release build now enables cross-module optimization for nine
interacting runtime units: cycles, interrupts, DMA, timers, CD-ROM, SIO,
memory, MDEC and SPU. MSVC compiles these with `/GL` and links with `/LTCG`.
The large generated game units retain their existing compilation settings.
`SHINKA_DEVICE_LTO=OFF` disables this build option for comparisons. Device
deadlines, transfer granularity and interrupt delivery logic are unchanged.

The Windows frame limiter now uses the existing high-resolution waitable
timer down to 200 microseconds before its deadline. The original millisecond
rounding could leave nearly two milliseconds of clock-polling per update.
The final short spin, original absolute deadlines, and 12-period catch-up
window remain. `SHINKA_PRECISE_PACING=OFF` restores the original limiter.
The framework checkout remains untouched; CMake generates a patched local
`frame_pacing.c`. Unsupported platforms retain the original limiter.

Twenty-second measurements from the same copied movie checkpoint, seven-second
warmup, ordinary speed, GL profiling disabled, following the user's OneDrive
shutdown:

| Build | Guest Hz | Process CPU ms/update | New audio underrun samples |
| --- | ---: | ---: | ---: |
| Prior build | 49.993 | 19.547 | 0 |
| Device LTO | 49.991 | 19.172 | 0 |
| Device LTO + reduced-spin pacing | 50.022 | 18.872 | 0 |

The final sample used about **3.5% less CPU per update** than the prior build.
This is a modest sequential-run result, not a claim of a large improvement or
an isolation of laptop-wide slowdown. CPU figures include all process threads;
100% utilization represents one logical core. Host clocks and scheduling can
vary between runs. Word-paced device scheduling remains expensive.

A timer-deadline cache and no-boundary update shortcut were also tried. They
matched the original implementation across all 1,024 timer modes and 200,000
mixed operations, but enabled/disabled samples were 19.953/20.000 ms per
update: no meaningful gain. That experiment was removed, including its hooks;
the retained build uses the original timer implementation with LTO.

The pacing regression test compiles the actual patched limiter with a
deterministic host clock. It covers overdue-deadline underflow, short sleeps,
different clock frequencies, 1,000 frames including late OS wakeups, transient
catch-up, and bounded re-anchoring. All ten Shinka native suites pass. Local
measurements and playback checks are retained under ignored `output/fmv-03/`.

Live validation observed the movie return naturally to the title screen and
confirmed Start still skips it. The copied battle held 49.966 updates/sec over
15 seconds, at 8.125 process CPU ms/update and zero new audio underrun samples.
Its frame-counted attack replay returned to the field; all 7,904 bytes of the
eight party records exactly matched the earlier verified battle outcome.
These samples do not establish whole-campaign coverage or resolve every
intermittent laptop-wide stall. Tests used the isolated save profile.

## Remaining movie cost: device-event scheduling — follow-up

Read-only profiling of the existing final movie build identified a large
movie-specific increase in global device scheduling work. No runtime behavior,
compiler options, or host settings were changed in this follow-up.

| Existing counter / measurement | Movie interval | Copied idle battle interval |
| --- | ---: | ---: |
| Guest updates/sec | 49.20 | 50.00 |
| Global deadline queries/sec | 3,234,398 | 200,609 |
| Device-advance passes/sec | 2,999,353 | 147,134 |
| Guest RAM stores/sec | 1,406,132 | 1,216,799 |
| Guest MMIO accesses/sec | 69,369 | 54,065 |
| Process CPU ms/guest update | 16.74 | 9.66 |

These are separate ten-second intervals, not an optimization A/B. The striking
difference is **16x the deadline queries and 20x the device-advance passes**, while
RAM store counts differ by only about 16%. Values were read from existing 64-bit
host counters using the running executable's linker-map addresses; the process
was not paused or written for these counter measurements. The SPU deadline and
service counters count the global scheduling visits here: each global deadline
query checks SPU timing and each `advance_devices` pass visits SPU service.

A separate five-second instruction-pointer sample (1,107 samples) repeatedly
landed in `timer_advance_counts` (55), `dma_cycles_to_internal_event` (47),
`dma_advance` (42), `psx_devices_service_to_now` (40), `psx_cyc_step` (50), and
`psx_cyc_charge` (42). Additional samples were spread across timer/CD/SPU deadline
queries and device advancement. These are sampled locations, not inclusive
call-stack percentages. Brief suspension perturbs timing; the sample is kept
separate from the unpaused cadence measurements.

The source explains the high event rate. A typical decoded opening frame holds
399,360 bytes (99,840 32-bit words). `dma_cycles_to_internal_event` exposes MDEC
output a word at a time, at the configured 14 guest cycles per output word.
At each event, `psx_devices_service_to_now` can advance a quiet prefix and then
the boundary cycle, visiting SIO, CD-ROM, DMA, timers, interrupts and SPU each
time. It also recomputes a global minimum deadline. Thus a word transfer causes
considerably more work than its RAM write. Actual per-word visibility and the
dependency order exist for correctness; simply copying a whole frame early
would change the guest timeline.

The next optimization target is therefore device-specific deadline retention
and deferred advancement of unrelated devices, with exact catch-up before
reads, writes and observable events. Any transfer batching must preserve when
guest RAM becomes visible and when completion/interrupts occur. Neither change
has been implemented or validated by this profiling pass.

### Intermittent stalls were not reproduced in the long sample

An unpaused 90-second observation, including the title/attract transition, held
49.991 guest updates/sec with **zero new host audio underrun samples**. One-second
cadence intervals ranged from 48.08 to 52.18 Hz as the deadline pacer caught up.
Movie-heavy 15-second windows used roughly 97–101% of one CPU core; the title
interval was lighter. The expensive scheduling path therefore leaves little
margin, but this run does not isolate the cause of every earlier long-run dip.

Concurrent host sampling averaged about 24% aggregate CPU use and 0.18 ms disk
transfer latency (maximum sampled average 0.98 ms). The processor-performance
counter stayed between 123.8% and 128.3% of its nominal reference; this is not a
temperature or per-core clock measurement. OneDrive still used at least 159 CPU
seconds over about 93 seconds (top-five-process sampling can omit smaller
intervals), while playback remained stable. OneDrive activity alone therefore
does not establish the cause of earlier stutter. No thermal or driver/DPC cause
was established.

Evidence and read-only sampling scripts: ignored `output/fmv-02/`. The diagnostic
process was closed afterward. The existing player profile and runner binary are
unchanged by this follow-up.

## Opening movie and shared scheduler — 2026-09-10

The opening STR movie now has an optional native unit generated from the owned
European `STDWTITL.PRO`. Eight audited routines cover MDEC input/output transfer,
wait/error handling, and the decoder reached through a function pointer. There
are 71 generated continuation entries in addition to the eight roots/ranges.
The pinned framework is unchanged; generated code remains local and ignored.

Two shared runtime costs were also identified with a five-second Windows
instruction-pointer sample, resolved through a local linker map:

* The audio event scheduler called `spu_get_global_state` merely to read SPUCNT.
  That snapshot scans all 24 voices and sweep registers. The two scheduler sites
  now read the identical register through `spu_read(0x1F801DAA)`. This address's
  read is side-effect-free and does not advance devices. Sample deadlines,
  IRQ conditions, and audio pumping are unchanged. `tools/runtime_perf.cmake`
  generates the patched `interrupts.c` and rejects changed call counts or newly
  used snapshot fields.
* Static overlay validation repeatedly computed CRCs. `src/overlay_guard.c`
  now retains immutable reference bytes after a successful CRC check and
  **compares every live code byte on every subsequent dispatch**. This does not
  cache a previous match result or trust a write-generation counter. References
  include the full range descriptions and checksum; allocation is bounded to
  1 MiB plus a 1,024-entry index. Full/failed allocations use the original CRC
  path. `SHINKA_GUARD_REFERENCE_CACHE=0` selects that path for comparison.

The later host sample no longer contained the full SPU snapshot or CRC routine
among its hottest functions. Sampling briefly suspends the diagnostic thread;
these samples identify host code, **not** smoothness or unbiased CPU percentages.

### Measurements and limits

Same copied opening-movie checkpoint, RX 6700S, GL timer queries off, ordinary
speed, and seven seconds of warmup:

| Build | Window | Guest Hz (target 50) | Process CPU / guest frame | New host underrun samples |
| --- | ---: | ---: | ---: | ---: |
| Initial baseline | 15 s | 32.53 | 32.18 ms | 229803 |
| Native movie + lean SPU read | 15 s | 50.02 | 19.87 ms | 0 |
| Final, also retaining checked reference bytes | 20 s | 49.73 | 21.01 ms | 3,692 |

The final short observation used about 35% less CPU per guest frame than the
initial baseline. These sequential runs had varying background load; do not
attribute their differences to one change in isolation. In particular, the
reference-cache addition is supported by removal of repeated CRC work, not by
the final run outperforming the earlier SPU-only run.

**Smooth playback is not fully solved.** Longer observations included dips
into the 40s and renewed underruns. One short 50-Hz/zero-underrun sample is not
a whole-movie guarantee. Remaining host samples emphasize cycle/device event
servicing; no timing shortcuts have been applied there.

Movie images were inspected, 8 seconds of newly produced SPU audio were captured,
the natural return to the title screen was observed, and Start also exited the
movie correctly. The opening then re-enters attract playback when left alone.
This validates the opening path, not every story/ending STR or subjective A/V
synchronization. The STR inventory contains additional movie files still to test.

A copied battle checkpoint subsequently held 50.06 Hz at 9.76 CPU ms/frame after
settling. An earlier interval immediately following movie-to-battle restoration
measured 39.10 Hz despite only 35.9% of one core of process CPU; retain it as an
outlier requiring investigation rather than silently dropping it. All nine
Shinka native suites and 81 Python tests passed. Guard regression tests now
change every code byte without write notifications and change range addresses
and lengths after a successful match. An unrestricted CTest run also found an
unbuilt dependency `example` target; the explicit nine-suite Shinka run passed.
The prior frame-counted basic-attack test was replayed after these changes and
returned to the field. All 7,904 bytes of the eight party records matched the
earlier native-battle result (`output/fmv-01/battle-parity.json`).

The generic idle-skip experiment and a movie-specific poll-boundary experiment
did not provide a worthwhile gain and were removed. `PSX_IDLE_SKIP` remains at
its previous default. An unsuccessful configuration attempt briefly launched
the previous executable; the `lean-spu-profile` attempt is invalid and excluded.
The verified SPU result is `lean-spu-verified-profile.json`.

### Reproduction

`tools/build_windows.ps1 -MovieNative` supplements `-OverlayCaptures`; it can be
combined with `-BattleNative`. Omitting a native switch clears its CMake source
option on that scripted build. For incremental generation:

```powershell
python tools/build_movie_native.py --module PATH/TO/STDWTITL.PRO --framework ../audit-recomp/psxrecomp --recompiler ../audit-recomp/build-recompiler/Release/psxrecomp-game.exe --output output/movie-native-NEW
cmake -S . -B build-windows -DSHINKA_MOVIE_OVERLAY_SOURCE=ABSOLUTE/PATH/TO/output/movie-native-NEW/overlays_static.c
cmake --build build-windows --config Release --target shinka
```

The helper rejects unsupported module hashes and unexpected generated coverage.
Supported module SHA-256:
`2a8cf1a9eedbacc47434a1dfb1afd45fd711af4216bb8f2d8a1f0e82bd629639`.
The local build uses `output/movie-native-01/overlays_static.c`.
`SHINKA_MOVIE_NATIVE=0` disables this optional unit per process. The baseline,
movie, and battle dispatchers retain live-byte validation and combined statistics.

Evidence, copied saves, logs, profiles, screenshots and exploratory sampling code
are under ignored `output/fmv-01/`. No player save was used for these writes.

### Whole-laptop responsiveness

In a 15.14-second sample, the game used 15.83 CPU seconds, with its main thread
accounting for 14.72 seconds. Process priority was Normal, working set about
672 MiB, and the renderer was the RX 6700S. Meanwhile `OneDrive.Sync.Service`
used 25.23 CPU seconds (about 1.67 cores). This repeats the earlier OneDrive
observation below. The checkout and diagnostic output are inside OneDrive.

Aggregate CPU and RAM percentages do not establish responsiveness: the movie
can be limited by one busy thread while other cores are available. Concurrent
sync work is an observed additional load; this does not prove it is caused by
the game or is the sole cause of desktop sluggishness. Temperatures, power limits,
disk latency, and driver/DPC latency were not established by this measurement.
No global priority, affinity, power, or OneDrive settings were changed.

## Guarded native battle geometry — 2026-09-10

After the user cleared the competing CPU work, two battle baselines measured
14.58 and 14.36 ms of process CPU per frame at 50 Hz. Compiling the hot entry
alone was unsuccessful as an optimization (16.81 ms/frame): interpreter
instruction accounting included work in its callees, and crossings between
the compiled entry and interpreted callees remained expensive. That isolated
entry build was superseded by a six-routine unit.

The retained optional native unit covers the connected geometry and primitive
construction routines rooted at `0x80085110`. All six live code ranges matched
the extracted `FIGHTSTG.PRO`; the final build is generated directly from that
module, with SHA-256
`92b6168a3d611bfc98e1c3da199d422dd05f76f6269496e393347155d52f7ab8`.
The generator admits only the audited six guarded ranges, plus their generated
continuation entries. Output stays ignored and contains no copied reference
repository source.

The final comparison used the **same executable**, with the native unit disabled
and enabled in separate processes. Both used RX 6700S, Chip music, 16:9, 80%
zoom, the copied Kunemon checkpoint, GL timer queries disabled, seven seconds of
warmup, and a 15-second measurement:

| Metric | Disabled | Enabled |
| --- | ---: | ---: |
| Process CPU / guest frame | 14.125 ms | 9.6875 ms |
| Process CPU, one-core equivalent | 70.61% | 48.41% |
| Guest cadence | 49.991 Hz | 49.970 Hz |
| Interpreted instructions / second | 6.63 million | 0.414 million |
| New audio underruns in the measurement | 0 | 0 |

This is **31.4% less process CPU time per frame in the tested idle battle**.
An earlier connected-routine run measured 10.99 ms/frame, also below baseline.
These are short local observations, not a campaign-wide or device-independent
performance guarantee. Animation rates, host pacing, and camera settings were
not changed to obtain the result.

Both paths replayed the same frame-counted attack inputs: Patamon dealt 815
damage, the battle completed, rewards were acknowledged, and Central Park
returned. All 7,904 bytes of the eight persistent party records were identical
afterward, as were the captured field-return states. Attack/recovery screenshots,
Tech and Item menus, and field return were inspected. This covers one basic
attack and its outcome; it does not establish spell, boss, multi-hit, or full
campaign parity. The 77 Python tests and nine native suites passed, including
the existing live-byte guard tests and new build-input/coverage rejection tests.

`src/battle_native.c` composes the new dispatcher with the existing baseline.
Every native entry retains `shinka_overlay_code_matches`; a changed or unrelated
overlay falls back. Code is not made eligible by address alone. Statistics sum
the two dispatchers, so address-miss counts include both attempted lookups.

### Rebuilding or disabling the native unit

Use `-BattleNative` alongside the existing `-OverlayCaptures` option in
`tools/build_windows.ps1`. It extracts the supported module, generates a fresh
local source, and passes `SHINKA_BATTLE_OVERLAY_SOURCE` to CMake. Omitting the
switch clears that optional source on the next scripted build. The baseline
overlay input is required; the new unit supplements it.

For incremental development with the baseline already built:

```powershell
python tools/build_battle_native.py --module PATH/TO/FIGHTSTG.PRO --framework ../audit-recomp/psxrecomp --recompiler ../audit-recomp/build-recompiler/Release/psxrecomp-game.exe --output output/battle-native-NEW
cmake -S . -B build-windows -DSHINKA_BATTLE_OVERLAY_SOURCE=ABSOLUTE/PATH/TO/output/battle-native-NEW/overlays_static.c
cmake --build build-windows --config Release --target shinka
```

The output directory must be new. Set `SHINKA_BATTLE_NATIVE=0` before launching
for an interpreter/baseline comparison without rebuilding. Normal launches of
a binary containing the unit enable it. This is a developer comparison switch,
not an animation-speed setting. The current local build uses
`output/battle-native-02/overlays_static.c`.

Evidence is in ignored `output/performance-02/`, including the raw comparison,
party-record snapshots, frame-counted replay script, screenshots, build logs,
and test output. The earlier single-entry experiment and first-pass outliers
are retained there or in `output/performance-01/`; they are not substituted for
the final measurements. The build generator can reproduce the guarded unit
without a running game or a RAM capture.

## First pass — 2026-09-10

The diagnostic runner initially selected `AMD Radeon(TM) Graphics` (integrated).
After setting Windows' per-executable high-performance preference, the same
OpenGL renderer reported `AMD Radeon RX 6700S`. Startup now logs both GL vendor
and renderer identity, so adapter selection can be checked directly.

The local preference applies to `build-windows/Release/dmw2003-shinka.exe` in
this checkout. Windows stores it under the executable's absolute path in
`HKCU\Software\Microsoft\DirectX\UserGpuPreferences` as `GpuPreference=2;`.
Moving the executable may require setting its preference again. The previous
value (absent) is recorded in the ignored local evidence directory.

These are **exploratory measurements under intermittent background CPU load**,
not controlled performance comparisons. The user confirmed competing CPU work;
one overlapping 40-second host sample also recorded approximately 50 CPU seconds
in OneDrive's sync service. No other processes were stopped or reconfigured.

Each observation below used a 12-second measurement after seven seconds of
settling. The copied diagnostic checkpoints were North Badland W (slot 9) and
the Kunemon battle waiting for input (slot 10). There was no automated attack
sequence in these measurements. Battle zoom was 80%; the alternate music was
Chip. The table uses dedicated-GPU runs with GL timer queries disabled.

| Scene/settings | Guest cadence | Process CPU per guest frame |
| --- | ---: | ---: |
| North Badland W, Chip | 50.04 Hz | 9.05 ms |
| Battle, widescreen, Chip (two observations) | 49.98–50.04 Hz | 14.33–15.49 ms |
| Battle, widescreen, Original music | 49.98 Hz | 15.31 ms |
| Battle, 4:3, Chip (repeat) | 50.04 Hz | 15.94 ms |

CPU time is summed across **all threads in the game process**, including driver
threads. It is not main-thread frame latency. At 50 Hz, 15 ms/frame represents
approximately 75% of one logical CPU core, not 75% of the entire machine.

An earlier 4:3 observation averaged 42.22 Hz with audio underruns, then returned
to 50.04 Hz on repetition. Preserve the outlier; it does not establish a
width-related regression. GPU-timer on/off results also varied, particularly
in the field. This pass establishes neither a dedicated-GPU speedup nor a
reliable benefit from disabling instrumentation. Playback defaults were not
changed based on those timings. Original/Chip music costs were close in the
sampled battle, but DS and Sampled were not compared here.

## Interpreting the existing counters

- `frame_perf.emu_cpu_ms_avg` is calculated as frame wall time minus presentation
  wall time. It includes pacing and must not be reported as actual CPU use.
- The GL scene query opens at the previous presentation exit and closes at the
  next presentation entry. Elapsed query intervals can span gaps while the CPU
  works or waits; the reported milliseconds are not GPU utilization percentages.
- `phase_profile` samples the execution-phase flag in wall time. A host wait can
  remain attributed to the enclosing guest/static phase. The field histogram's
  dominant static address (`0x8002e7fc`, a polling/wait routine in the reference
  disassembly) therefore does not establish an expensive CPU function by itself.
- `phase_hot` is cumulative, with only the top 64 entries exposed. Retain before
  and after snapshots; a single snapshot includes earlier scenes.
- `dispatch_native` counts the dynamic overlay route. This build also uses
  statically compiled overlays: inspect `static_hits` before concluding that
  everything is interpreted. Static hits were present in this run.

## Strongest next leads

The battle cadence log reports roughly 6.3 million interpreted instructions per
second, compared with about 1.0 million in the stationary field. Battle wall
sampling attributed about 59% to the interpreter in representative windows.
This supports investigating CPU-side battle work before changing renderers.

In the original-music battle window, interpreter accounting attributed about
67.6 million instructions to entry `0x00085110`. The reference battle-stage
listing contains a function at `0x80085110` which begins with geometry-coprocessor
matrix operations. This is a useful lead for battle geometry processing, not
yet an identified animation clock or a proven exclusive CPU hotspot. Verify
live overlay bytes and the interpreter counter's inclusive accounting before
reconstructing or compiling that path.

Next, repeat the same checkpoints under quiet CPU conditions and measure actual
attacks separately from idle battle rendering. Use native CPU stack sampling to
distinguish interpreter dispatch, geometry calculations, sound mixing, code
validation, and graphics-driver work. Any expansion of compiled overlay coverage
must preserve Shinka's live-byte validation: stale overlay execution previously
caused a real partner-selection crash. Do not disable that guard for speed.

## Reusable measurement tool

Launch a diagnostic instance with a copied save directory, a dedicated debug
port, and these process-local environment variables:

```powershell
$env:PSX_RUNTIME_PERF_DIAG = '1'
$env:PSX_RUNTIME_PERF_DIAG_MS = '2000'
$env:PSX_GL_PERF = '0' # use 1 in a separate instrumentation comparison
```

Then, using the PID of that instance:

```powershell
python tools/profile_runtime.py --pid <PID> --scene battle-chip-wide --slot 10 --seconds 12 --output output/performance-next/battle.json
```

The tool uses Windows `GetProcessTimes` for CPU accounting, records guest-frame
progress, and saves raw audio, interpreter, overlay and rendering diagnostics.
It loads a checkpoint only when `--slot` is supplied and does not change game
settings. It refuses to overwrite a report. Its six-second minimum warmup flushes
the 256-frame render ring only when the game is keeping PAL cadence; slower
scenes require a longer warmup. It does not launch the process or verify that
the supplied PID owns the chosen debug port; match both to the diagnostic run.

Local evidence is under ignored `output/performance-01/`: JSON reports, startup
and cadence logs, adapter inventory, CPU snapshots, and the preference backup.
The diagnostic runner was stopped after this pass. Player settings matched the
pre-test file byte-for-byte; player memory cards were not used for profiling.
The GPU identity logging change built successfully and the profiler completed
live field/battle measurements. No game-logic optimization was shipped in this
pass; the GPU preference and diagnostic tooling are the concrete changes.
