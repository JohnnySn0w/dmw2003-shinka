# Host caller-stack profiling

The Windows x64 sampler records the active function **and its callers** from an
isolated Shinka runner. This helps distinguish transfer work from callbacks that
present frames, wait for pacing, or collect diagnostics inside device service.
It does not require recompiling the game, patching guest memory, installing a
driver, or downloading symbols.

## Build and capture

Build the standalone tool with Visual Studio's C++ tools and the Windows SDK:

```powershell
cmake -S tools/host_profiler -B output/host-profiler/build -A x64
cmake --build output/host-profiler/build --config Release
```

Launch a **separate test runner with a copied save profile**, restore the desired
checkpoint, and allow at least seven seconds of warmup. Supply its exact PID:

```powershell
$testProcess = Get-Process -Id <isolated-test-process-id>
$testThread = $testProcess.Threads |
  Sort-Object TotalProcessorTime -Descending | Select-Object -First 1
& output/host-profiler/build/Release/profile_host_stack.exe `
  $testProcess.Id $testThread.Id 10 output/host-profiler/movie-stacks.json
python tools/summarize_host_stacks.py output/host-profiler/movie-stacks.json `
  --map output/title-screen/release/dmw2003-shinka.map `
  --output output/host-profiler/movie-summary.json
```

The busiest accumulated thread is a useful starting point for this runner,
not a universal thread-selection rule. Inspect thread CPU activity if the
process has been running for a long time or its workload has changed. Capture
other active threads separately when investigating audio or driver work.

The map must belong to the exact executable sampled. The sampler records loaded
module bases, sizes, and PE timestamps; the summarizer checks the game timestamp
and records a map hash. Archives from the initial prototype fall back to checking
the executable on disk. System DLLs are labeled by module and offset. Duplicate
addresses from identical-code folding retain all map aliases.

## Interpretation and limits

The tool briefly suspends only the chosen thread to copy its register context
and up to 256 KiB of its committed stack. It resumes that thread before unwinding,
symbol loading, output, or allocation. The unwinder uses the copied stack and
refuses live reads from uncopied portions of that stack region. RAII restores
the suspension count on ordinary errors. Do not forcibly terminate the sampler
while it is capturing a thread; use the bounded 1–60 second duration.

Samples use randomized 3–7 ms intervals to reduce frame-period aliasing. The
output includes leaf counts, unique inclusive counts, caller edges, folded
stacks, stack depths, and snapshot-duration statistics. Recursion counts once
per inclusive function per sample. Return addresses are resolved at the
preceding byte so a call ending on a function boundary is not mislabeled.

**These percentages describe sampled wall-time residency, not CPU time.** A
thread sleeping beneath the scheduler still has the scheduler in its stack.
Frame pacing and graphics-driver waits must not be charged as device computation.
Inlining and tail calls hide frames; nearest-function map labels are approximate,
not source-line attribution. Check stack depths and the depth-limit count for
incomplete unwinds. The chosen thread also excludes work in other process threads.

Use `profile_scheduler.py` in separate, unsampled runs to measure process CPU,
guest cadence, and audio underruns. Do not compile or run another diagnostic
sampler during an acceptance measurement. Repeat with reversed order and the
same checkpoint/settings before calling a small difference an improvement.

## Retrospective RAM-write history

Shinka also leaves the catch-all RAM-write recorder off by default. Its
4,194,304 entries occupy 128 MiB and otherwise receive a record on every
eligible traced store. Enable it before launching a forensic session:

```powershell
$env:PSX_WRITE_HISTORY = '1'
```

Unset, empty, or values beginning with `0` leave it disabled. This is a
process-start option; `wtrace_all_stats.enabled` reports whether the buffer
was allocated. `wtrace_all_dump` explains how to enable an unavailable buffer;
`wtrace_all_reset` does not allocate one. Allocation failure also reports
disabled. History cannot be recovered retroactively from a run without it.

Explicitly armed address-range traces (`wtrace_arm` / `wtrace_dump`), write
fingerprints, guest counters, and code-write invalidation remain independent.
The existing movie diagnostic quiet policy can suppress writes in either
mode; use `PSX_DEBUG_FMV_QUIET=0` only in a separate diagnostic session when
complete movie traces are needed. Do not mix that recording session with
normal-play performance comparisons.

## Continuous display history

Shinka defaults the expensive pixel-history recorder off. This avoids two GPU
readbacks at each eligible frame and an 84 MiB pixel-history allocation. It does
not disable the debug server, input routes, one-shot screenshots, presented-frame
captures, or GP0 command history.

For exact historical-frame renderer comparisons, explicitly enable it **before
launching the test process**:

```powershell
$env:PSX_DISPLAY_RING = '1'
# Launch the isolated test runner, then query display_ring_stats/get/aux.
```

Unset, empty, or `0` leaves it off. The setting is read once per process.
`display_ring_stats` reports no retained frames when disabled; history cannot
be recovered retroactively. The movie's existing quiet-mode policy still skips
some debug recording while MDEC is recently active, even when history is enabled.
