# Partner-selection abnormal exit: first report

Status: unresolved; first observed on the Windows baseline with static boot/movie overlays. The user reached partner selection through cutscenes and dialogue and reported that effects and visuals looked correct until the failure. They were holding Tab for fast-forward as the selection screen loaded. Exact selected set/action and whether turbo is necessary to reproduce remain unknown.

The visible-host log ends with `execution completed, PC=0x00000000`. The runtime's corresponding path identifies this as an abnormal return from top-level guest dispatch. This is evidence of a guest control-flow exit, not evidence of a Windows access violation. Do not attribute it to controller support or turbo alone without a paired reproduction.

Preserved locally under ignored `output/crashes/partner-selection-20260909/`: visible-host log, exit trace, last-run report, final heartbeat, and available freeze dumps. Raw artifacts contain game memory and are not tracked.

Most reliable terminal state comes from the final heartbeat and explicit exit trace:

- Frame 13,191; PC `0x00000000`; RA `0x8008312C`; SP `0x1F8003CC`.
- Last recorded store `0x80025168`, in a byte-copy loop. A last-store address alone does not identify the cause.
- No unsupported-interpreter opcode or unknown-dispatch entries were reported.
- Explicit exit trace has zero recorded function entries, so it cannot identify the transfer that published zero.
- The last-run report's CPU fields disagree with the explicit trace/heartbeat and include apparent host-address fragments. Treat those late CPU fields as unreliable until report lifetime is investigated.
- Available automatic freeze dumps are from early boot (frames 407/423), not from partner selection. No player-run savestate was found.

Next reproduction should save immediately before partner selection, then compare the same transition with Tab released and held. If it fails, retain live guest state with the launcher's `-HoldOnGuestExit` switch. This uses the pinned runtime's `PSX_EXIT_HALT` diagnostic path, which keeps the debug server available after this specific null-PC exit instead of immediately shutting down. It is not a fix or a general Windows-crash handler.

Then inspect the transition caller, loaded overlay bytes, and the transfer producing PC zero. Compare static-overlay and fallback execution if the same checkpoint reproduces the failure. Do not redirect PC or bypass the selection logic merely to keep the window open.
