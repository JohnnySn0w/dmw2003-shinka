# Pause while minimized

Offline gameplay automatically pauses when the Windows game window is minimized.
Restoring the window resumes it. Focus loss alone does not pause: leaving the
game visible while using another app keeps the existing behavior. This does not
change CPU cost during active play.

The game stops advancing frames and issuing new rendering work. Queued audio
drains naturally, and connected controllers receive a rumble-stop request.
Restore resets the host frame deadline, fades audio back in, and uses the
existing release guard to keep held window-management buttons out of gameplay.
The save-state and runtime-settings overlays also sleep when minimized.

The default is enabled, without changing saved preferences. For diagnostics,
set the process environment variable `SHINKA_PAUSE_MINIMIZED=0` to retain the
old behavior. Headless runs, absent windows, and the framework's active netplay
path bypass the pause. The debug server is serviced by the emulation thread;
requests wait while minimized, so restore the window before using navigation
or profiling commands. External process CPU accounting remains available.

## Implementation

`src/minimize_pause.inc` is included in Shinka's owned frontend copy through
`tools/minimize_pause.cmake`. It runs at the existing VBlank boundary, before
frame work, and inside the three existing host pause loops. It checks the live
SDL minimized flag and sleeps in 50 ms increments while pumping window-close
and controller connection events. Close uses the normal shutdown path, including
memory-card flushes. Other key events are consumed without triggering hotkeys.
The starvation watchdog receives heartbeats throughout the suspension.

Only host pacing, input guard, rumble tracking and audio fade/diagnostic state
are adjusted. The helper does not modify guest RAM, advance CPU/SPU/CD clocks,
or reset game rendering state. Controller reconnection uses the existing device
selection path. Physical reconnect and rumble behavior still need hardware tests.

## Verification — 2026-09-11

The Windows Release build and all 16 native regression suites passed. The new
test compiles the actual helper with deterministic window/event stubs, covering
suspension, timed sleeping, device events, rumble-stop requests, input guarding,
timing reset, and bypass for visible/headless/netplay/disabled configurations.

Live checks used copied saves and the actual Windows minimize control:

- Central Park paused and restored at frame 1589; movement and the quick menu
  worked after restore.
- The F7 save-state menu paused and restored at frame 3487, retaining its menu
  and selection. Closing it returned to the battle.
- The battle paused and restored at frame 4165; subsequent menu input worked.
- During a confirmed minimized field interval, the process used 0.109375 CPU
  seconds over 8.031668 wall seconds: **0.0136 CPU cores**, or 1.36% of one core.
  This is process CPU consumption, not whole-machine utilization or GPU usage.

Initial diagnostic launches were hidden, so attempted minimize actions on those
windows did not establish the minimized state. Their roughly 0.4-core samples
are excluded from before/after minimized comparisons. The valid measurement
above came from an explicitly visible launch, a confirmed minimize action and
matching pause/restore log markers. No percentage improvement against the old
minimized behavior is claimed. Local reports are in `output/minimize-01/`.

Movie playback, mid-save suspension, physical controller reconnects and closing
directly from a minimized taskbar entry have not been tested live in this pass.
Player cards and installed preferences were preserved.
